import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MahavitranApiClient
from .statistics import MahavitranStatisticsManager
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_CONSUMER_NO, CONF_AMISP_CODE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mahavitran from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    consumer_no = entry.data.get(CONF_CONSUMER_NO)
    amisp_code = entry.data.get(CONF_AMISP_CODE)
    
    # Get update interval from options, fallback to default
    update_interval_mins = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES)
    update_interval = timedelta(minutes=update_interval_mins)

    session = async_get_clientsession(hass)
    api = MahavitranApiClient(username, password, session, consumer_no, amisp_code)
    stats_manager = MahavitranStatisticsManager(hass, consumer_no)

    # Immediately register external statistic metadata so it is available in the Energy Dashboard dropdown
    await stats_manager.async_initialize_metadata()

    # We import here to avoid circular imports
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
    
    async def async_update_data():
        """Fetch data from API and update statistics."""
        try:
            data = await api.async_get_smart_meter_data()
            current_reading = 0.0
            if data and isinstance(data.get("current_reading"), dict):
                try:
                    current_reading = float(data["current_reading"].get("READING", 0.0))
                except (ValueError, TypeError):
                    pass

            if data and "days_data" in data and data["days_data"]:
                try:
                    sums = await stats_manager.async_inject_daily_data(data["days_data"], current_reading)
                    data["cumulative_import_sum"] = sums.get("import_sum", 0.0)
                    data["cumulative_export_sum"] = sums.get("export_sum", 0.0)
                except Exception as ex:
                    _LOGGER.error("Failed to inject historical statistics: %s", ex, exc_info=True)
            else:
                # If daily data is empty due to API timeout/glitch, fallback to last computed sums to preserve state
                sums = stats_manager.get_last_sums()
                if data is None:
                    data = {}
                data["cumulative_import_sum"] = sums.get("import_sum", 0.0)
                data["cumulative_export_sum"] = sums.get("export_sum", 0.0)
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="mahavitran_smart_meter",
        update_method=async_update_data,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "stats_manager": stats_manager,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register update listener to reload integration when options change
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
