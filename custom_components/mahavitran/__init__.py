import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MahavitranApiClient
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_CONSUMER_NO, CONF_AMISP_CODE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mahavitran from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    consumer_no = entry.data.get(CONF_CONSUMER_NO)
    amisp_code = entry.data.get(CONF_AMISP_CODE, "002")

    session = async_get_clientsession(hass)
    api = MahavitranApiClient(username, password, consumer_no, amisp_code, session)

    # Validate login & token
    try:
        await api.async_login()
    except Exception as ex:
        _LOGGER.error("Failed to authenticate with Mahavitran during setup: %s", ex)
        return False

    hass.data[DOMAIN][entry.entry_id] = api
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
