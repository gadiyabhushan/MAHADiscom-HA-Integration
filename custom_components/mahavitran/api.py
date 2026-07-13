import logging
import aiohttp
from typing import Dict, Any, List
import base64
from Crypto.Cipher import AES
import json

_LOGGER = logging.getLogger(__name__)

# Base URLs
MOBILE_APP_URL = "https://mobileapp.mahadiscom.in/App_Requests"
SMART_METER_URL = "https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.0.0"
AES_KEY = b"3MKDMK4555232322BB5929E8E033BC69"

class MahavitranApiClient:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession, consumer_no: str = None, amisp_code: str = None) -> None:
        """Initialize API client."""
        self.username = username
        self.password = password
        self._session = session
        self.consumer_no = consumer_no
        self.amisp_code = amisp_code
        self._token = None
        
    def _encrypt_password(self, password: str) -> str:
        """Encrypt password using AES ECB mode with PKCS5 padding, just like the app."""
        cipher = AES.new(AES_KEY, AES.MODE_ECB)
        pwd_bytes = password.encode('utf-8')
        pad_len = 16 - (len(pwd_bytes) % 16)
        padded_pwd = pwd_bytes + bytes([pad_len] * pad_len)
        encrypted = cipher.encrypt(padded_pwd)
        return base64.b64encode(encrypted).decode('utf-8')

    async def async_login(self) -> Dict[str, Any]:
        """Login to the Mahavitran App API and return AccountDetails."""
        try:
            encrypted_password = self._encrypt_password(self.password)
            payload = {
                "loginId": self.username,
                "pass": encrypted_password,
                "deviceOS": "ANDROID",
                "appVersion": 169
            }

            async with self._session.post(
                f"{MOBILE_APP_URL}/SignIn",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("ResponseStatus") == "SUCCESS":
                        if data.get("AccountExist") == "NO":
                            return {"success": False, "error": "Account does not exist"}
                            
                        self._token = data.get("token", "dummy_token")
                        account_details = data.get("AccountDetails", [])
                        
                        # The API returns AccountDetails as a JSON string inside the JSON response
                        if isinstance(account_details, str):
                            try:
                                account_details = json.loads(account_details)
                            except json.JSONDecodeError:
                                _LOGGER.error("Failed to parse AccountDetails JSON string")
                                account_details = []
                                
                        return {"success": True, "consumers": account_details}
                    else:
                        return {"success": False, "error": "Invalid username or password"}
                else:
                    return {"success": False, "error": f"HTTP Error {response.status}"}

        except Exception as e:
            _LOGGER.error(f"Error during Mahavitran login: {e}")
            return {"success": False, "error": str(e)}

    def _get_basic_auth(self) -> aiohttp.BasicAuth:
        """Return HTTP Basic Auth for Smart Meter API endpoints."""
        return aiohttp.BasicAuth(self.username, self.password)

    def _get_smart_meter_headers(self) -> Dict[str, str]:
        """Headers required by Smart Meter API."""
        return {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169",
            "Content-Type": "application/json"
        }

    async def async_get_smart_meter_data(self) -> Dict[str, Any]:
        """Fetch all relevant smart meter data for the configured consumer."""
        if not self.consumer_no or not self.amisp_code:
            return {"status": "Not Configured"}
            
        result_data = {
            "status": "Connected",
            "current_reading": None,
        }

        # 1. Fetch Current Reading
        try:
            url = f"{SMART_METER_URL}/{self.amisp_code}/GetCurrentReading/{self.consumer_no}"
            async with self._session.get(
                url,
                auth=self._get_basic_auth(),
                headers=self._get_smart_meter_headers(),
                timeout=10
            ) as response:
                if response.status == 200:
                    result_data["current_reading"] = await response.json()
                elif response.status == 500:
                    _LOGGER.warning("GetCurrentReading returned 500 Internal Server Error (possibly closed meter).")
                    result_data["status"] = "Failed (Closed Meter?)"
                else:
                    _LOGGER.debug(f"GetCurrentReading failed with status {response.status}")
                    result_data["status"] = "Failed"
        except Exception as e:
            _LOGGER.debug(f"Failed to fetch Current Reading: {e}")
            result_data["status"] = "Failed"
            
        return result_data
