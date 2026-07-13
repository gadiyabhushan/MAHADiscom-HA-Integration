import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Mahavitran button platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([MahavitranForceUpdateButton(coordinator, entry)])


class MahavitranForceUpdateButton(CoordinatorEntity, ButtonEntity):
    """Button to force an update of the Mahavitran API data."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._consumer_no = entry.data.get("consumer_no", "unknown")

    @property
    def unique_id(self) -> str:
        """Return unique ID for the button."""
        return f"mahavitran_{self._consumer_no}_force_update"

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return "Force Update"

    @property
    def icon(self) -> str:
        """Return the icon of the button."""
        return "mdi:update"

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._consumer_no)},
            "name": f"Mahavitran Smart Meter ({self._consumer_no})",
            "manufacturer": "Mahavitran",
            "model": "Smart Meter",
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Force update requested for Mahavitran Smart Meter")
        await self.coordinator.async_request_refresh()
