import logging
import aiohttp
from typing import Dict, Any, List
import base64
from Crypto.Cipher import AES
import datetime

_LOGGER = logging.getLogger(__name__)

# Base URLs
MOBILE_APP_URL = "https://mobileapp.mahadiscom.in/App_Requests"
SMART_METER_URL = "https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.0.0"
AES_KEY = b"3MKDMK4555232322BB5929E8E033BC69"

class MahavitranApiClientError(Exception):
    """Exception to indicate a general API error."""

class MahavitranAuthError(MahavitranApiClientError):
    """Exception to indicate an authentication error."""

class MahavitranApiClient:
    def __init__(self, username: str, password: str, consumer_no: str, amisp_code: str, session: aiohttp.ClientSession) -> None:
        self._username = username
        self._password = password
        self._consumer_no = consumer_no
        self._amisp_code = amisp_code
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

    def _get_basic_auth(self) -> aiohttp.BasicAuth:
        """Return HTTP Basic Auth for Smart Meter API endpoints."""
        return aiohttp.BasicAuth(self._username, self._password)

    def _get_smart_meter_headers(self) -> Dict[str, str]:
        """Headers required by Smart Meter API."""
        return {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169",
            "Content-Type": "application/json"
        }

    async def async_login(self) -> Dict[str, Any]:
        """Login to the Mahavitran App API and return AccountDetails."""
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
                        if data.get("AccountExist") == "NO":
                            _LOGGER.error("Mahavitran Login Failed: Account does not exist.")
                            raise MahavitranAuthError("Account does not exist")
                            
                        self._token = data.get("token", "dummy_token")
                        return data.get("AccountDetails", {})
                    else:
                        _LOGGER.error("Mahavitran Login Failed: %s", data)
                        raise MahavitranAuthError("Invalid username or password")
                else:
                    _LOGGER.error("Mahavitran HTTP Error: %s", response.status)
                    raise MahavitranApiClientError(f"HTTP Error {response.status}")

        except aiohttp.ClientError as err:
            _LOGGER.error("Connection to Mahavitran API failed: %s", err)
            raise MahavitranApiClientError(f"Connection error: {err}")

    async def async_get_smart_meter_data(self) -> Dict[str, Any]:
        """Get Smart Meter data from the API."""
        if not self._token:
            await self.async_login()
            
        if not self._consumer_no or not self._amisp_code:
             return {"status": "error", "message": "No consumer number or amisp_code provided."}

        # Initialize the result dict
        result_data = {
            "status": "connected",
            "current_reading": None,
            "daily_consumption": None,
            "hourly_consumption": None,
            "monthly_consumption": None
        }

        now = datetime.datetime.now()

        # 1. Fetch Current Reading
        try:
            url = f"{SMART_METER_URL}/{self._amisp_code}/GetCurrentReading/{self._consumer_no}"
            async with self._session.get(
                url,
                auth=self._get_basic_auth(),
                headers=self._get_smart_meter_headers()
            ) as response:
                if response.status == 200:
                    result_data["current_reading"] = await response.json()
                else:
                    _LOGGER.debug("GetCurrentReading failed with status %s", response.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch Current Reading: %s", e)

        # 2. Fetch Daily Consumption (yyyyMM)
        try:
            daily_month = now.strftime("%Y%m")
            url = f"{SMART_METER_URL}/{self._amisp_code}/GetDailyConsumption/{self._consumer_no}/{daily_month}"
            async with self._session.get(
                url,
                auth=self._get_basic_auth(),
                headers=self._get_smart_meter_headers()
            ) as response:
                if response.status == 200:
                    result_data["daily_consumption"] = await response.json()
                else:
                     _LOGGER.debug("GetDailyConsumption failed with status %s", response.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch Daily Consumption: %s", e)

        # 3. Fetch Hourly Consumption (yyyyMMdd)
        try:
            hourly_day = now.strftime("%Y%m%d")
            url = f"{SMART_METER_URL}/{self._amisp_code}/GetHourlyConsumption/{self._consumer_no}/{hourly_day}"
            async with self._session.get(
                url,
                auth=self._get_basic_auth(),
                headers=self._get_smart_meter_headers()
            ) as response:
                if response.status == 200:
                    result_data["hourly_consumption"] = await response.json()
                else:
                     _LOGGER.debug("GetHourlyConsumption failed with status %s", response.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch Hourly Consumption: %s", e)

        # 4. Fetch Monthly Consumption (yyyy)
        try:
            monthly_year = now.strftime("%Y")
            url = f"{SMART_METER_URL}/{self._amisp_code}/GetMonthlyConsumption/{self._consumer_no}/{monthly_year}"
            async with self._session.get(
                url,
                auth=self._get_basic_auth(),
                headers=self._get_smart_meter_headers()
            ) as response:
                if response.status == 200:
                    result_data["monthly_consumption"] = await response.json()
                else:
                     _LOGGER.debug("GetMonthlyConsumption failed with status %s", response.status)
        except Exception as e:
            _LOGGER.debug("Failed to fetch Monthly Consumption: %s", e)


        return result_data
