import logging
from datetime import datetime
from typing import Dict, Any, List

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.storage import Store
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "mahavitran_stats_"


class MahavitranStatisticsManager:
    """Manages continuous historical statistics for Mahavitran smart meters."""

    def __init__(self, hass: HomeAssistant, consumer_no: str) -> None:
        self.hass = hass
        self.consumer_no = consumer_no
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{consumer_no}")
        self._data: Dict[str, Any] = {
            "day_base_sums": {"import": {}, "export": {}},
            "day_totals": {"import": {}, "export": {}},
        }
        self._loaded = False

    async def _async_load(self) -> None:
        """Load stored stats base data."""
        if not self._loaded:
            stored = await self._store.async_load()
            if stored and isinstance(stored, dict):
                self._data["day_base_sums"]["import"].update(stored.get("day_base_sums", {}).get("import", {}))
                self._data["day_base_sums"]["export"].update(stored.get("day_base_sums", {}).get("export", {}))
                self._data["day_totals"]["import"].update(stored.get("day_totals", {}).get("import", {}))
                self._data["day_totals"]["export"].update(stored.get("day_totals", {}).get("export", {}))
            self._loaded = True

    async def _async_save(self) -> None:
        """Persist stats base data."""
        await self._store.async_save(self._data)

    async def _get_initial_seed(self, stat_id: str, default_seed: float = 0.0) -> float:
        """Get the last known statistic sum from recorder if storage is empty."""
        try:
            last_stats = await self.hass.async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
            if last_stats and stat_id in last_stats and last_stats[stat_id]:
                val = last_stats[stat_id][0].get("sum")
                if val is not None and float(val) > 0:
                    return float(val)
        except Exception as e:
            _LOGGER.debug("Could not fetch last statistics for %s: %s", stat_id, e)
        return default_seed

    async def async_inject_daily_data(
        self, days_data: List[Dict[str, Any]], current_reading: float = 0.0
    ) -> Dict[str, float]:
        """
        Process and inject hourly statistics for given dates in chronological order.
        
        Returns dict with current cumulative import and export sums.
        """
        await self._async_load()

        import_entity_id = f"sensor.mahavitran_{self.consumer_no}_import_historical_sensor"
        export_entity_id = f"sensor.mahavitran_{self.consumer_no}_export_historical_sensor"

        import_meta = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Mahavitran Import Historical (Dashboard)",
            source="recorder",
            statistic_id=import_entity_id,
            unit_of_measurement="kWh",
        )

        export_meta = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name="Mahavitran Export Historical (Dashboard)",
            source="recorder",
            statistic_id=export_entity_id,
            unit_of_measurement="kWh",
        )

        if not days_data:
            return {"import_sum": 0.0, "export_sum": 0.0}

        import_stats: List[StatisticData] = []
        export_stats: List[StatisticData] = []

        local_tz = dt_util.get_time_zone(self.hass.config.time_zone) or dt_util.DEFAULT_TIME_ZONE

        # Sort dates in ascending order
        sorted_days = sorted(days_data, key=lambda d: d.get("date", ""))

        last_import_sum = 0.0
        last_export_sum = 0.0

        for day_entry in sorted_days:
            date_str = day_entry.get("date")
            hourly_list = day_entry.get("hourly")
            if not date_str or not isinstance(hourly_list, list) or not hourly_list:
                continue

            try:
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
            except (ValueError, IndexError):
                continue

            # Ensure we have a continuous baseline sum for this date
            for kind, stat_id, seed_fallback in [
                ("import", import_entity_id, current_reading),
                ("export", export_entity_id, 0.0),
            ]:
                if date_str not in self._data["day_base_sums"][kind]:
                    prev_dates = sorted([d for d in self._data["day_base_sums"][kind].keys() if d < date_str])
                    if prev_dates:
                        last_prev_date = prev_dates[-1]
                        prev_base = self._data["day_base_sums"][kind][last_prev_date]
                        prev_total = self._data["day_totals"][kind].get(last_prev_date, 0.0)
                        self._data["day_base_sums"][kind][date_str] = prev_base + prev_total
                    else:
                        seed = await self._get_initial_seed(stat_id, seed_fallback)
                        self._data["day_base_sums"][kind][date_str] = seed

            # Parse and sort hourly items for this date
            parsed_hours = []
            for item in hourly_list:
                try:
                    h = int(item.get("HOUR", 0))
                    imp = float(item.get("UNITS_IMPORTED", item.get("READING", 0.0)))
                    exp = float(item.get("UNITS_EXPORTED", 0.0))
                    parsed_hours.append((h, imp, exp))
                except (ValueError, TypeError):
                    continue

            parsed_hours.sort(key=lambda x: x[0])

            # Process Import statistics
            imp_running = self._data["day_base_sums"]["import"][date_str]
            imp_day_total = 0.0
            for h, imp_val, _ in parsed_hours:
                imp_running += imp_val
                imp_day_total += imp_val

                start_h = (h - 1) if (1 <= h <= 24) else h
                start_local = datetime(year, month, day, start_h, 0, 0, tzinfo=local_tz)
                start_utc = dt_util.as_utc(start_local)

                import_stats.append(
                    StatisticData(
                        start=start_utc,
                        state=round(imp_running, 4),
                        sum=round(imp_running, 4),
                    )
                )
            self._data["day_totals"]["import"][date_str] = imp_day_total
            last_import_sum = imp_running

            # Process Export statistics
            exp_running = self._data["day_base_sums"]["export"][date_str]
            exp_day_total = 0.0
            for h, _, exp_val in parsed_hours:
                exp_running += exp_val
                exp_day_total += exp_val

                start_h = (h - 1) if (1 <= h <= 24) else h
                start_local = datetime(year, month, day, start_h, 0, 0, tzinfo=local_tz)
                start_utc = dt_util.as_utc(start_local)

                export_stats.append(
                    StatisticData(
                        start=start_utc,
                        state=round(exp_running, 4),
                        sum=round(exp_running, 4),
                    )
                )
            self._data["day_totals"]["export"][date_str] = exp_day_total
            last_export_sum = exp_running

        # Save base sums for future updates
        await self._async_save()

        # Inject statistics into recorder database
        if import_stats:
            async_import_statistics(self.hass, import_meta, import_stats)
            _LOGGER.debug("Injected %d import statistics for %s", len(import_stats), import_entity_id)

        if export_stats:
            async_import_statistics(self.hass, export_meta, export_stats)
            _LOGGER.debug("Injected %d export statistics for %s", len(export_stats), export_entity_id)

        return {"import_sum": last_import_sum, "export_sum": last_export_sum}
