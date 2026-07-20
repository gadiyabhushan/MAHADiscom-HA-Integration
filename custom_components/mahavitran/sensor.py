import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

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
    """Sensor for Cumulative Hourly Consumption (sum of today's hourly readings)."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_cumulative_hourly"

    @property
    def name(self):
        return "Cumulative Hourly Consumption Today"

    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def state_class(self):
        # TOTAL_INCREASING allows HA to track this cumulatively even when it resets to 0 at midnight
        return SensorStateClass.TOTAL_INCREASING

    @property
    def state(self):
        if self.coordinator.data and self.coordinator.data.get("hourly_consumption"):
            hourly_data = self.coordinator.data["hourly_consumption"]
            if isinstance(hourly_data, list):
                total = 0.0
                for entry in hourly_data:
                    reading = entry.get("READING")
                    if reading is not None:
                        try:
                            total += float(reading)
                        except (ValueError, TypeError):
                            pass
                return round(total, 2)
        return None

    @property
    def unit_of_measurement(self):
        return "kWh"
