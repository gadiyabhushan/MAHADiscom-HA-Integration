import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_CONSUMER_NO, CONF_AMISP_CODE
from .api import MahavitranApiClient, MahavitranAuthError

_LOGGER = logging.getLogger(__name__)

class MahavitranConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mahavitran."""

    VERSION = 1

    def __init__(self):
        self.username = None
        self.password = None
        self.consumer_list = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.username = user_input[CONF_USERNAME]
            self.password = user_input[CONF_PASSWORD]

            # Initialize API and try to login to fetch consumer list
            session = async_get_clientsession(self.hass)
            api = MahavitranApiClient(self.username, self.password, "", "", session)
            
            try:
                login_data = await api.async_login()
                # Assuming login_data contains the full AccountDetails dict
                if login_data and "ConsumerList" in login_data:
                    self.consumer_list = login_data["ConsumerList"]
                    if not self.consumer_list:
                        errors["base"] = "no_consumers_found"
                    else:
                        return await self.async_step_select_consumer()
                else:
                    errors["base"] = "invalid_auth"

            except MahavitranAuthError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_select_consumer(self, user_input=None):
        """Prompt user to select a consumer number."""
        errors = {}
        
        # Build dict for dropdown mapping ConNumber -> Display Name
        consumers = {
            c.get("ConNumber"): f"{c.get('ConName', 'Unknown')} ({c.get('ConNumber')})"
            for c in self.consumer_list
            if c.get("ConNumber")
        }

        if user_input is not None:
            selected_no = user_input[CONF_CONSUMER_NO]
            
            # Find the amispCode for the selected consumer
            selected_consumer = next((c for c in self.consumer_list if c.get("ConNumber") == selected_no), None)
            amisp_code = selected_consumer.get("amispCode", "002") if selected_consumer else "002"

            return self.async_create_entry(
                title=f"Mahavitran ({selected_no})",
                data={
                    CONF_USERNAME: self.username,
                    CONF_PASSWORD: self.password,
                    CONF_CONSUMER_NO: selected_no,
                    CONF_AMISP_CODE: amisp_code,
                }
            )

        schema = vol.Schema({
            vol.Required(CONF_CONSUMER_NO): vol.In(consumers),
        })

        return self.async_show_form(
            step_id="select_consumer", data_schema=schema, errors=errors
        )
