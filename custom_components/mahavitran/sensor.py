import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Mahavitran sensor platform."""
    api = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        """Fetch data from API."""
        try:
            return await api.async_get_smart_meter_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="mahavitran_smart_meter",
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    entities = [
        MahavitranStatusSensor(coordinator, entry),
        MahavitranCurrentReadingSensor(coordinator, entry),
        MahavitranDailyConsumptionSensor(coordinator, entry),
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
    def state(self):
        if self.coordinator.data and self.coordinator.data.get("current_reading"):
            reading_data = self.coordinator.data["current_reading"]
            if isinstance(reading_data, dict):
                return reading_data.get("CURRENT_READING", "unknown")
        return "unavailable"

    @property
    def unit_of_measurement(self):
        return "kWh"


class MahavitranDailyConsumptionSensor(MahavitranSensorBase):
    """Sensor for Daily Consumption."""

    @property
    def unique_id(self):
        return f"mahavitran_{self._consumer_no}_daily_consumption"

    @property
    def name(self):
        return "Latest Daily Consumption"

    @property
    def state(self):
        if self.coordinator.data and self.coordinator.data.get("daily_consumption"):
            daily_data = self.coordinator.data["daily_consumption"]
            # It usually returns a list of dictionaries for the month.
            # We fetch the latest one with a valid reading.
            if isinstance(daily_data, list):
                for entry in reversed(daily_data):
                    reading = entry.get("READING")
                    if reading is not None:
                        return reading
        return "unavailable"

    @property
    def unit_of_measurement(self):
        return "kWh"

    @property
    def extra_state_attributes(self):
        """Return the date of the latest reading as an attribute."""
        if self.coordinator.data and self.coordinator.data.get("daily_consumption"):
            daily_data = self.coordinator.data["daily_consumption"]
            if isinstance(daily_data, list):
                for entry in reversed(daily_data):
                    reading = entry.get("READING")
                    if reading is not None:
                        return {"reading_date": entry.get("DATE", "unknown")}
        return {}
