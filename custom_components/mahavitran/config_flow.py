import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_CONSUMER_NO, CONF_PASSWORD

class MahavitranConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mahavitran."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # We can perform a test login here if we had the correct API payload
            # For now, we accept any input since we are testing
            return self.async_create_entry(
                title=user_input[CONF_CONSUMER_NO], 
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Required(CONF_CONSUMER_NO): str,
            vol.Optional(CONF_PASSWORD, description={"suggested_value": ""}): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )
