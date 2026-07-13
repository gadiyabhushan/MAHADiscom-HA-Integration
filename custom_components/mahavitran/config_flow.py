import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD

class MahavitranConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mahavitran."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"Mahavitran - {user_input[CONF_USERNAME]}", 
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )
