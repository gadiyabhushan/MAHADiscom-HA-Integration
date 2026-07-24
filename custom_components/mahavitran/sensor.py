import logging
from datetime import timedelta, datetime
from homeassistant.util import dt as dt_util

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Mahavitran sensor platform."""
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        MahavitranStatusSensor(coordinator, entry),
        MahavitranCurrentReadingSensor(coordinator, entry),
        MahavitranCumulativeHourlySensor(coordinator, entry),
        MahavitranHourlyExportSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class MahavitranSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Mahavitran sensors."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._consumer_no = entry.data.get("consumer_no", "unknown")

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._consumer_no)},
            "name": f"Mahavitran Smart Meter ({self._consumer_no})",
            "manufacturer": "Mahavitran",
            "model": "Smart Meter",
        }


class MahavitranStatusSensor(MahavitranSensorBase):
    """Sensor for Mahavitran Connection Status."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_status"

    @property
    def name(self):
        return "Connection Status"

    @property
    def state(self):
        if self.coordinator.data:
            return self.coordinator.data.get("status", "unknown")
        return "unknown"


class MahavitranCurrentReadingSensor(MahavitranSensorBase):
    """Sensor for Current Meter Reading."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_current_reading"

    @property
    def name(self):
        return "Current Reading"

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        # This is the cumulative meter! This is the ONLY sensor the HA Energy Dashboard actually needs.
        return SensorStateClass.TOTAL_INCREASING

    @property
    def state(self):
        if self.coordinator.data and self.coordinator.data.get("current_reading"):
            reading_data = self.coordinator.data["current_reading"]
            if isinstance(reading_data, dict):
                return reading_data.get("READING")
        return None

    @property
    def unit_of_measurement(self):
        return "kWh"


class MahavitranCumulativeHourlySensor(MahavitranSensorBase):
    """Sensor for Cumulative Hourly Consumption (sum of today's hourly import readings)."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_cumulative_hourly_import"

    @property
    def name(self):
        return "Cumulative Hourly Import Today"

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        # TOTAL_INCREASING allows HA to track this cumulatively even when it resets to 0 at midnight
        return SensorStateClass.TOTAL_INCREASING

    @property
    def state(self):
        if self.coordinator.data and "today_import" in self.coordinator.data:
            return round(self.coordinator.data["today_import"], 2)
        return None

    @property
    def extra_state_attributes(self):
        """Return the raw hourly data as attributes."""
        attrs = {}
        if self.coordinator.data and "hourly_consumption" in self.coordinator.data:
            hourly_list = self.coordinator.data["hourly_consumption"]
            if isinstance(hourly_list, list):
                # Format as a clean dictionary: {"00:00": 0.5, "01:00": 0.8, ...}
                breakdown = {}
                for entry in hourly_list:
                    hour = entry.get("HOUR", "00")
                    val = float(entry.get("UNITS_IMPORTED", entry.get("READING", 0.0)))
                    breakdown[f"{hour}:00"] = val
                attrs["hourly_breakdown"] = breakdown
        return attrs

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()
        self._inject_historical_statistics()

    def _inject_historical_statistics(self):
        """Inject historical statistics directly into the recorder database."""
        if not self.entity_id or not self.hass:
            return
            
        if not self.coordinator.data or "hourly_consumption" not in self.coordinator.data:
            return
            
        hourly_list = self.coordinator.data["hourly_consumption"]
        if not isinstance(hourly_list, list) or not hourly_list:
            return
            
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"Mahavitran Import Historical ({self._consumer_no})",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:import_historical_{self._consumer_no}",
            unit_of_measurement="kWh",
        )
        
        running_sum = 0.0
        statistics = []
        
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for entry in hourly_list:
            hour_str = entry.get("HOUR")
            if hour_str is None:
                continue
                
            try:
                hour_int = int(hour_str)
                val = float(entry.get("UNITS_IMPORTED", entry.get("READING", 0.0)))
                running_sum += val
                
                start_time = today_start + timedelta(hours=hour_int)
                
                statistics.append(
                    StatisticData(
                        start=start_time,
                        state=running_sum,
                        sum=running_sum
                    )
                )
            except (ValueError, TypeError):
                continue
                
        if statistics:
            async_import_statistics(self.hass, metadata, statistics)

    @property
    def unit_of_measurement(self):
        return "kWh"


class MahavitranHourlyExportSensor(MahavitranSensorBase):
    """Sensor for Cumulative Hourly Export (sum of today's hourly export readings)."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_cumulative_hourly_export"

    @property
    def name(self):
        return "Cumulative Hourly Export Today"

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        return SensorStateClass.TOTAL_INCREASING

    @property
    def state(self):
        if self.coordinator.data and "today_export" in self.coordinator.data:
            return round(self.coordinator.data["today_export"], 2)
        return None

    @property
    def extra_state_attributes(self):
        """Return the raw hourly data as attributes."""
        attrs = {}
        if self.coordinator.data and "hourly_consumption" in self.coordinator.data:
            hourly_list = self.coordinator.data["hourly_consumption"]
            if isinstance(hourly_list, list):
                # Format as a clean dictionary: {"00:00": 0.5, "01:00": 0.8, ...}
                breakdown = {}
                for entry in hourly_list:
                    hour = entry.get("HOUR", "00")
                    val = float(entry.get("UNITS_EXPORTED", 0.0))
                    breakdown[f"{hour}:00"] = val
                attrs["hourly_breakdown"] = breakdown
        return attrs

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        super()._handle_coordinator_update()
        self._inject_historical_statistics()

    def _inject_historical_statistics(self):
        """Inject historical statistics directly into the recorder database."""
        if not self.entity_id or not self.hass:
            return
            
        if not self.coordinator.data or "hourly_consumption" not in self.coordinator.data:
            return
            
        hourly_list = self.coordinator.data["hourly_consumption"]
        if not isinstance(hourly_list, list) or not hourly_list:
            return
            
        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=True,
            name=f"Mahavitran Export Historical ({self._consumer_no})",
            source=DOMAIN,
            statistic_id=f"{DOMAIN}:export_historical_{self._consumer_no}",
            unit_of_measurement="kWh",
        )
        
        running_sum = 0.0
        statistics = []
        
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for entry in hourly_list:
            hour_str = entry.get("HOUR")
            if hour_str is None:
                continue
                
            try:
                hour_int = int(hour_str)
                val = float(entry.get("UNITS_EXPORTED", 0.0))
                running_sum += val
                
                start_time = today_start + timedelta(hours=hour_int)
                
                statistics.append(
                    StatisticData(
                        start=start_time,
                        state=running_sum,
                        sum=running_sum
                    )
                )
            except (ValueError, TypeError):
                continue
                
        if statistics:
            async_import_statistics(self.hass, metadata, statistics)

    @property
    def unit_of_measurement(self):
        return "kWh"
