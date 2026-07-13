import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_CONSUMER_NO, CONF_AMISP_CODE, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
from .api import MahavitranApiClient

_LOGGER = logging.getLogger(__name__)

class MahavitranConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mahavitran."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self.username = None
        self.password = None
        self.consumers = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.username = user_input[CONF_USERNAME]
            self.password = user_input[CONF_PASSWORD]
            
            session = async_get_clientsession(self.hass)
            api = MahavitranApiClient(self.username, self.password, session)
            
            result = await api.async_login()
            
            if result.get("success"):
                self.consumers = result.get("consumers", [])
                if not self.consumers:
                    errors["base"] = "no_consumers"
                else:
                    return await self.async_step_select_consumer()
            else:
                errors["base"] = "invalid_auth"

        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_select_consumer(self, user_input=None):
        """Handle consumer selection step."""
        errors = {}

        if user_input is not None:
            selected_no = user_input[CONF_CONSUMER_NO]
            selected_consumer = next((c for c in self.consumers if c["CONSUMER_NO"] == selected_no), None)
            
            if selected_consumer:
                return self.async_create_entry(
                    title=f"Mahavitran - {selected_consumer.get('CONSUMER_NAME', selected_no)}",
                    data={
                        CONF_USERNAME: self.username,
                        CONF_PASSWORD: self.password,
                        CONF_CONSUMER_NO: selected_no,
                        CONF_AMISP_CODE: selected_consumer.get("AMISP_CODE", "")
                    },
                )
            else:
                errors["base"] = "invalid_selection"

        # Build dropdown options
        consumer_options = {
            c["CONSUMER_NO"]: f"{c.get('CONSUMER_NAME', 'Unknown')} ({c['CONSUMER_NO']})"
            for c in self.consumers
        }

        data_schema = vol.Schema({
            vol.Required(CONF_CONSUMER_NO): vol.In(consumer_options),
        })

        return self.async_show_form(
            step_id="select_consumer", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MahavitranOptionsFlowHandler(config_entry)


class MahavitranOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MINUTES
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
