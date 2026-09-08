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
    StatisticMeanType,
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
            "max_sums": {"import": 0.0, "export": 0.0},
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
                if "max_sums" in stored and isinstance(stored["max_sums"], dict):
                    self._data["max_sums"].update(stored["max_sums"])
            self._loaded = True

    async def _async_save(self) -> None:
        """Persist stats base data."""
        await self._store.async_save(self._data)

    def get_last_sums(self) -> Dict[str, float]:
        """Return the last computed import and export sums from memory."""
        self._data.setdefault("max_sums", {"import": 0.0, "export": 0.0})
        import_sum = self._data["max_sums"].get("import", 0.0)
        export_sum = self._data["max_sums"].get("export", 0.0)
        
        # Fallback to day_base_sums + day_totals if max_sums is 0.0
        for kind in ["import", "export"]:
            dates = sorted(self._data["day_base_sums"][kind].keys())
            if dates:
                last_date = dates[-1]
                base = self._data["day_base_sums"][kind][last_date]
                total = self._data["day_totals"][kind].get(last_date, 0.0)
                calculated = base + total
                if kind == "import":
                    import_sum = max(import_sum, calculated)
                else:
                    export_sum = max(export_sum, calculated)
                    
        return {"import_sum": import_sum, "export_sum": export_sum}

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

    async def async_initialize_metadata(self) -> None:
        """Register the statistic metadata immediately so it appears in the Energy Dashboard dropdown."""
        from homeassistant.helpers import entity_registry as er
        entity_reg = er.async_get(self.hass)
        
        # Get actual entity_id from unique_id if it exists in registry (e.g. customized or renamed)
        import_unique_id = f"mahavitran_{self.consumer_no}_import_historical_sensor"
        import_entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, import_unique_id)
        if not import_entity_id:
            import_entity_id = f"sensor.mahavitran_{self.consumer_no}_import_historical_sensor"

        export_unique_id = f"mahavitran_{self.consumer_no}_export_historical_sensor"
        export_entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, export_unique_id)
        if not export_entity_id:
            export_entity_id = f"sensor.mahavitran_{self.consumer_no}_export_historical_sensor"

        import_meta = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Mahavitran Import Historical (Dashboard)",
            source="recorder",
            statistic_id=import_entity_id,
            unit_of_measurement="kWh",
            unit_class="energy",
        )

        export_meta = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Mahavitran Export Historical (Dashboard)",
            source="recorder",
            statistic_id=export_entity_id,
            unit_of_measurement="kWh",
            unit_class="energy",
        )

        try:
            async_import_statistics(self.hass, import_meta, [])
            async_import_statistics(self.hass, export_meta, [])
            _LOGGER.debug("Registered statistics metadata for %s and %s", import_entity_id, export_entity_id)
        except Exception as err:
            _LOGGER.debug("Error initializing statistic metadata: %s", err)

    async def async_inject_daily_data(
        self, days_data: List[Dict[str, Any]], current_reading: float = 0.0
    ) -> Dict[str, float]:
        """
        Process and inject hourly statistics for given dates in chronological order.
        
        Returns dict with current cumulative import and export sums.
        """
        await self._async_load()

        from homeassistant.helpers import entity_registry as er
        entity_reg = er.async_get(self.hass)
        
        # Get actual entity_id from unique_id if it exists in registry
        import_unique_id = f"mahavitran_{self.consumer_no}_import_historical_sensor"
        import_entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, import_unique_id)
        if not import_entity_id:
            import_entity_id = f"sensor.mahavitran_{self.consumer_no}_import_historical_sensor"

        export_unique_id = f"mahavitran_{self.consumer_no}_export_historical_sensor"
        export_entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, export_unique_id)
        if not export_entity_id:
            export_entity_id = f"sensor.mahavitran_{self.consumer_no}_export_historical_sensor"

        import_meta = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Mahavitran Import Historical (Dashboard)",
            source="recorder",
            statistic_id=import_entity_id,
            unit_of_measurement="kWh",
            unit_class="energy",
        )

        export_meta = StatisticMetaData(
            has_mean=False,
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Mahavitran Export Historical (Dashboard)",
            source="recorder",
            statistic_id=export_entity_id,
            unit_of_measurement="kWh",
            unit_class="energy",
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

            # Initialize hourly_cache dict for date_str if missing
            self._data.setdefault("hourly_cache", {})
            self._data["hourly_cache"].setdefault(date_str, {"import": {}, "export": {}})
            day_cache = self._data["hourly_cache"][date_str]

            # 1. Process Import statistics
            imp_running = self._data["day_base_sums"]["import"][date_str]
            imp_day_total = 0.0
            for h, imp_val, _ in parsed_hours:
                imp_running += imp_val
                imp_day_total += imp_val

                # Monotonic upper bound per hour
                prev_hour_sum = day_cache["import"].get(str(h), 0.0)
                cached_sum = max(prev_hour_sum, imp_running)
                day_cache["import"][str(h)] = cached_sum

            prev_imp_total = self._data["day_totals"]["import"].get(date_str, 0.0)
            self._data["day_totals"]["import"][date_str] = max(prev_imp_total, imp_day_total)

            # Build import_stats from all cached hours for date_str in order
            for h_str in sorted(day_cache["import"].keys(), key=lambda x: int(x)):
                h_int = int(h_str)
                cached_val = day_cache["import"][h_str]
                start_h = (h_int - 1) if (1 <= h_int <= 24) else h_int
                start_local = datetime(year, month, day, start_h, 0, 0, tzinfo=local_tz)
                start_utc = dt_util.as_utc(start_local).replace(minute=0, second=0, microsecond=0)
                import_stats.append(
                    StatisticData(
                        start=start_utc,
                        state=round(cached_val, 4),
                        sum=round(cached_val, 4),
                    )
                )
                last_import_sum = max(last_import_sum, cached_val)

            # 2. Process Export statistics
            exp_running = self._data["day_base_sums"]["export"][date_str]
            exp_day_total = 0.0
            for h, _, exp_val in parsed_hours:
                exp_running += exp_val
                exp_day_total += exp_val

                # Monotonic upper bound per hour
                prev_hour_sum = day_cache["export"].get(str(h), 0.0)
                cached_sum = max(prev_hour_sum, exp_running)
                day_cache["export"][str(h)] = cached_sum

            prev_exp_total = self._data["day_totals"]["export"].get(date_str, 0.0)
            self._data["day_totals"]["export"][date_str] = max(prev_exp_total, exp_day_total)

            # Build export_stats from all cached hours for date_str in order
            for h_str in sorted(day_cache["export"].keys(), key=lambda x: int(x)):
                h_int = int(h_str)
                cached_val = day_cache["export"][h_str]
                start_h = (h_int - 1) if (1 <= h_int <= 24) else h_int
                start_local = datetime(year, month, day, start_h, 0, 0, tzinfo=local_tz)
                start_utc = dt_util.as_utc(start_local).replace(minute=0, second=0, microsecond=0)
                export_stats.append(
                    StatisticData(
                        start=start_utc,
                        state=round(cached_val, 4),
                        sum=round(cached_val, 4),
                    )
                )
                last_export_sum = max(last_export_sum, cached_val)

        # Enforce strict monotonic non-decreasing bounds on cumulative sums
        self._data.setdefault("max_sums", {"import": 0.0, "export": 0.0})
        if last_import_sum > 0:
            last_import_sum = max(self._data["max_sums"].get("import", 0.0), last_import_sum)
            self._data["max_sums"]["import"] = last_import_sum
        else:
            last_import_sum = self._data["max_sums"].get("import", 0.0)

        if last_export_sum > 0:
            last_export_sum = max(self._data["max_sums"].get("export", 0.0), last_export_sum)
            self._data["max_sums"]["export"] = last_export_sum
        else:
            last_export_sum = self._data["max_sums"].get("export", 0.0)

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
