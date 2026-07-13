import logging
import aiohttp
from typing import Dict, Any, List
import base64
from Crypto.Cipher import AES

_LOGGER = logging.getLogger(__name__)

# Base URLs
MOBILE_APP_URL = "https://mobileapp.mahadiscom.in/App_Requests"
SMART_METER_URL = "https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.0.0/002"

class MahavitranApiClient:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession, consumer_no: str = None, amisp_code: str = None) -> None:
        """Initialize API client."""
        self.username = username
        self.password = password
        self._session = session
        self.consumer_no = consumer_no
        self.amisp_code = amisp_code
        self._key = b"V6A1L2I4D6A8T0IO"
        
    def _pad(self, text: str) -> str:
        """Pad text for AES encryption."""
        padding_len = 16 - (len(text) % 16)
        return text + (chr(padding_len) * padding_len)
        
    def _encrypt(self, text: str) -> str:
        """Encrypt payload with AES ECB."""
        cipher = AES.new(self._key, AES.MODE_ECB)
        padded_text = self._pad(text)
        encrypted_bytes = cipher.encrypt(padded_text.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    async def async_login(self) -> Dict[str, Any]:
        """Authenticate with the Mahavitran App API and get AccountDetails."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        # Structure observed from decompiled code
        payload = f"V_{self.username}|{self.password}"
        encrypted_payload = self._encrypt(payload)
        
        data = {
            "Login_Name": self.username,
            "Parameters": encrypted_payload,
            "Method_Name": "Login"
        }
        
        try:
            async with self._session.post(
                MOBILE_APP_URL, 
                headers=headers, 
                data=data,
                timeout=10
            ) as response:
                response.raise_for_status()
                json_response = await response.json()
                
                # Verify successful login
                if json_response.get("Method_Status") == "Success":
                    # Parse the nested AccountDetails JSON string
                    account_details_str = json_response.get("AccountDetails", "[]")
                    import json
                    try:
                        account_details = json.loads(account_details_str)
                        return {"success": True, "consumers": account_details}
                    except json.JSONDecodeError:
                        return {"success": False, "error": "Failed to parse AccountDetails"}
                else:
                    return {"success": False, "error": json_response.get("Method_Message", "Login failed")}
                    
        except Exception as e:
            _LOGGER.error(f"Error during Mahavitran login: {e}")
            return {"success": False, "error": str(e)}

    async def _async_get_smart_meter_endpoint(self, endpoint: str) -> Any:
        """Helper to fetch smart meter API endpoints using Basic Auth."""
        if not self.consumer_no:
            _LOGGER.error("Cannot fetch smart meter data: consumer_no not set")
            return None
            
        url = f"{SMART_METER_URL}/{endpoint}"
        auth = aiohttp.BasicAuth(self.username, self.password)
        headers = {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169"
        }
        
        try:
            async with self._session.get(url, auth=auth, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    _LOGGER.warning(f"Smart meter endpoint {endpoint} returned status {response.status}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error fetching smart meter endpoint {endpoint}: {e}")
            return None

    async def async_get_smart_meter_data(self) -> Dict[str, Any]:
        """Fetch all relevant smart meter data for the configured consumer."""
        if not self.consumer_no:
            return {"status": "Not Configured"}
            
        # Get Current Meter Health (contains the actual live meter reading)
        meter_health = await self._async_get_smart_meter_endpoint(f"GetMeterHealth/{self.consumer_no}")
        
        # Construct combined data payload (removed the heavy hourly/daily/monthly calls)
        data = {
            "status": "Connected" if meter_health else "Failed",
            "current_reading": meter_health,
        }
        
        return data
