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
        base_url = f"https://mobileapp.mahadiscom.in/consappsmartmeterapi-2.0.0/{AMISP_CODE}"
        
        # Comprehensive list of possible endpoint names
        prefixes = ["Get", "Fetch", "Retrieve"]
        types = ["Hourly", "Daily", "Net", "Solar", "Export", "Import", "Prosumer", "Generation", "Consumption", "Meter"]
        
        # Add the most likely ones manually first
        endpoints_to_try = [
            "GetHourlyExport", "GetHourlyImport", "GetSolarHourly", "GetSolarHourlyConsumption", 
            "GetNetHourly", "GetNetMeterHourly", "GetHourlyGeneration", "GetExportData", 
            "GetImportExportData", "GetHourlyExportData", "GetSolarData", "GetSolarHourlyData",
            "GetNetHourlyData", "GetHourlyNetConsumption", "GetHourlySolarConsumption",
            "GetHourlySolar", "GetHourlyNet", "GetSmartMeterHourlyData", "GetProsumerHourlyConsumption",
            "GetProsumerHourlyData", "GetSolarHourlyExport", "GetSolarHourlyImport", 
            "GetHourlySolarExport", "GetHourlySolarImport", "GetProsumerConsumption",
            "GetSolarGeneration", "GetHourlySolarGeneration", "GetSolarExport",
            "GetNetMeterHourlyConsumption", "GetHourlyNetMeter", "GetSolarExportHourly",
            "GetHourlyImportExport", "GetHourlyExportImport", "GetProsumerHourly",
            "GetHourlyProsumer", "GetSolarExportData", "GetSolarImportData",
            "GetSmartMeterHourly", "GetSmartMeterExport", "GetNetConsumption",
            "GetSolarNetConsumption", "GetSolarNetHourly", "GetHourlySolarNet",
            "GetHourlyExportNet", "GetExportHourlyNet", "GetSolarHourlyNet"
        ]
        
        auth = aiohttp.BasicAuth(USERNAME, PASSWORD)
        headers = {
            "Client-Os": "ANDROID",
            "Client-Os-Version": "13",
            "Client-Version": "169",
            "Content-Type": "application/json"
        }
        
        print(f"Testing {len(endpoints_to_try)} possible endpoints...")
        
        for endpoint in endpoints_to_try:
            url = f"{base_url}/{endpoint}/{CONSUMER_NO}/{hourly_day}"
            try:
                async with session.get(url, auth=auth, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"\n✅ SUCCESS! Found valid endpoint: {endpoint}")
                        print(json.dumps(data, indent=2)[:500] + "\n... (truncated)")
                        return
                    elif response.status == 500:
                        print(f"\n⚠️ FOUND ENDPOINT (but got 500 Error): {endpoint}")
                        print(f"This means the URL exists but might need a different date format or parameters.")
                        return
                    # We ignore 404s to keep the output clean
            except Exception as e:
                pass
                
        print("\n❌ Tested all endpoints, none returned data. Mahavitran must have used a very obscure name.")

if __name__ == "__main__":
    asyncio.run(main())
