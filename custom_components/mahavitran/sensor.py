from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy
from .const import DOMAIN
from homeassistant.helpers.update_coordinator import CoordinatorEntity

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Mahavitran sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        MahavitranCurrentReadingSensor(coordinator, entry),
    ])

class MahavitranCurrentReadingSensor(CoordinatorEntity, SensorEntity):
    """Sensor for displaying the current smart meter reading."""

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_name = f"Mahavitran Meter {config_entry.data.get('consumer_no')} Reading"
        self._attr_unique_id = f"mahavitran_{config_entry.data.get('consumer_no')}_current_reading"
        
        # Proper HA properties for Energy Dashboard
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Using the coordinator data fetched in api.py
        # You will likely need to adjust the dictionary keys based on the exact API response!
        data = self.coordinator.data
        if not data:
            return None
        
        # Example JSON parsing based on common practices
        # Replace 'currentReading' with actual key when known
        return data.get("currentReading")

    @property
    def extra_state_attributes(self):
        """Return extra state attributes (e.g. timestamp of reading)."""
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "reading_date": data.get("readingDate")
        }
