import logging
import aiohttp
from typing import Dict, Any

_LOGGER = logging.getLogger(__name__)

# Base URLs
MOBILE_APP_URL = "https://mobileapp.mahadiscom.in/App_Requests"
WSS_URL = "https://wss.mahadiscom.in/wss/wss" # Alternate API if WSS login is used

class MahavitranApiClient:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str, consumer_no: str):
        self.session = session
        self.username = username
        self.password = password
        self.consumer_no = consumer_no
        self.token = None
        self.amisp = "Unknown"

    async def authenticate(self) -> bool:
        """Authenticate with the API."""
        # This uses a placeholder for the login endpoint since we are reversing it
        # You mentioned it uses username/password and no OTP.
        url = f"{MOBILE_APP_URL}/Login" # Update this to exact path once known
        payload = {"username": self.username, "password": self.password}
        
        try:
            # We are testing different endpoints based on the strings we found
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Auth success: %s", data)
                    self.token = data.get("token", "dummy_token")
                    self.amisp = data.get("amisp", "MSEDCL") # Example fallback
                    return True
                else:
                    _LOGGER.error("Auth failed with status %s on URL %s", response.status, url)
                    return False
        except Exception as e:
            _LOGGER.error("Error authenticating: %s", e)
            return False

    async def get_current_reading(self) -> Dict[str, Any]:
        """Fetch the current smart meter reading."""
        if not self.token:
            success = await self.authenticate()
            # If auth fails, we can still try to return something or halt
            if not success:
                _LOGGER.error("Halting reading fetch due to auth failure.")
                return {}
            
        url = f"{MOBILE_APP_URL}/{self.amisp}/GetCurrentReading/{self.consumer_no}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug("Current reading data: %s", data)
                    return data
                else:
                    _LOGGER.error("Failed to get reading, status %s on URL %s", response.status, url)
        except Exception as e:
            _LOGGER.error("Error fetching reading: %s", e)
        return {}
