import asyncio
import aiohttp
import json

# Replace with your credentials and meter details
USERNAME = "gadiyabhushan1"
PASSWORD = "Gadiya@100"  
CONSUMER_NO = "110013829691" # e.g., 110012151870
AMISP_CODE = "002"   # e.g., 002

import base64
from Crypto.Cipher import AES
from datetime import datetime

AES_KEY = b"3MKDMK4555232322BB5929E8E033BC69"

def encrypt_password(password: str) -> str:
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    pwd_bytes = password.encode('utf-8')
    pad_len = 16 - (len(pwd_bytes) % 16)
    padded_pwd = pwd_bytes + bytes([pad_len] * pad_len)
    encrypted = cipher.encrypt(padded_pwd)
    return base64.b64encode(encrypted).decode('utf-8')

async def main():
    async with aiohttp.ClientSession() as session:
        # Get hourly data directly using basic auth
        now = datetime.now()
        hourly_day = now.strftime("%Y%m%d")
        url = f"https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.0.0/{AMISP_CODE}/GetHourlyConsumption/{CONSUMER_NO}/{hourly_day}"
        
        auth = aiohttp.BasicAuth(USERNAME, PASSWORD)
        headers = {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169",
            "Content-Type": "application/json"
        }
        
        print(f"Fetching: {url}")
        async with session.get(url, auth=auth, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("SUCCESS! Here is the JSON data:")
                print(json.dumps(data, indent=2))
            else:
                print(f"FAILED with status: {response.status}")
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(main())
