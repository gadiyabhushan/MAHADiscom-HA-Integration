import asyncio
import aiohttp
import json
from datetime import datetime

# Replace with your details
USERNAME = "gadiyabhushan1"
PASSWORD = "Gadiya@100"  
CONSUMER_NO = "110013829691" # e.g., 110012151870
AMISP_CODE = "002"

async def main():
    async with aiohttp.ClientSession() as session:
        now = datetime.now()
        hourly_day = now.strftime("%Y%m%d")
        base_url = f"https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.1.0/{AMISP_CODE}"
        
        endpoints_to_try = [
            "GetHourlyConsumption"
        ]
        
        auth = aiohttp.BasicAuth(USERNAME, PASSWORD)
        headers = {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169",
            "Content-Type": "application/json"
        }
        
        print("Starting endpoint discovery...")
        for endpoint in endpoints_to_try:
            url = f"{base_url}/{endpoint}/{CONSUMER_NO}/{hourly_day}"
            print(f"Testing: {endpoint}...")
            
            try:
                async with session.get(url, auth=auth, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\nSUCCESS! Found valid endpoint: {endpoint}")
                        print(json.dumps(data, indent=2)[:500] + "\n... (truncated)")
                    elif response.status == 404:
                        print("  ❌ 404 Not Found")
                    elif response.status == 500:
                        print("  ❌ 500 Internal Server Error (Endpoint might exist but expects different parameters)")
                    else:
                        print(f"  ⚠️ {response.status}")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
