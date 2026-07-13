import logging
import aiohttp
from typing import Dict, Any
import base64
from Crypto.Cipher import AES

_LOGGER = logging.getLogger(__name__)

# Base URLs
MOBILE_APP_URL = "https://mobileapp.mahadiscom.in/App_Requests"
AES_KEY = b"3MKDMK4555232322BB5929E8E033BC69"

class MahavitranApiClientError(Exception):
    """Exception to indicate a general API error."""

class MahavitranAuthError(MahavitranApiClientError):
    """Exception to indicate an authentication error."""

class MahavitranApiClient:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        self._username = username
        self._password = password
        self._session = session
        self._token = None

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password using AES ECB mode with PKCS5 padding, just like the app."""
        cipher = AES.new(AES_KEY, AES.MODE_ECB)
        pwd_bytes = password.encode('utf-8')
        pad_len = 16 - (len(pwd_bytes) % 16)
        padded_pwd = pwd_bytes + bytes([pad_len] * pad_len)
        encrypted = cipher.encrypt(padded_pwd)
        return base64.b64encode(encrypted).decode('utf-8')

    async def async_login(self) -> bool:
        """Login to the Mahavitran App API."""
        try:
            encrypted_password = self._encrypt_password(self._password)
            payload = {
                "loginId": self._username,
                "pass": encrypted_password,
                "deviceOS": "ANDROID",
                "appVersion": 169
            }

            async with self._session.post(
                f"{MOBILE_APP_URL}/SignIn",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("ResponseStatus") == "SUCCESS":
                        # Usually, the token or auth info is returned here. 
                        # We consider it a success if ResponseStatus is SUCCESS.
                        if data.get("AccountExist") == "NO":
                            _LOGGER.error("Mahavitran Login Failed: Account does not exist.")
                            raise MahavitranAuthError("Account does not exist")
                            
                        self._token = data.get("token") # Assuming it returns a token
                        return True
                    else:
                        _LOGGER.error("Mahavitran Login Failed: %s", data)
                        raise MahavitranAuthError("Invalid username or password")
                else:
                    _LOGGER.error("Mahavitran HTTP Error: %s", response.status)
                    raise MahavitranApiClientError(f"HTTP Error {response.status}")

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection to Mahavitran API failed: %s", err)
            raise MahavitranApiClientError(f"Connection error: {err}")

    async def async_get_data(self) -> Dict[str, Any]:
        """Get data from the API."""
        if not self._token:
            await self.async_login()

        # Currently we just return empty data or some dummy data until we decode the fetching endpoints.
        # Once we have login working perfectly on HA, we'll fetch actual smart meter data.
        return {
            "status": "connected",
            "message": "Login successful. Meter data endpoints pending implementation."
        }
