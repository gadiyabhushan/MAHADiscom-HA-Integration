from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import MahavitranApiClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class MahavitranCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Mahavitran data."""

    def __init__(self, hass, api: MahavitranApiClient):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self):
        """Update data via library."""
        try:
            data = await self.api.get_current_reading()
            if not data:
                raise UpdateFailed("Error fetching data from Mahavitran API")
            return data
        except Exception as exception:
            raise UpdateFailed(exception) from exception
