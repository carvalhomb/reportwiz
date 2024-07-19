import os
import requests
import json
from datetime import datetime, timedelta
 
def fetch_nasa_power_data(config):
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    longitude, latitude, _ = config["geometry"]["coordinates"]
    start_date = config["header"]["start"]
    end_date = config["header"]["end"]
    params_list = ",".join(config["properties"]["parameter"].keys())
 
    parameters = {
        "start": start_date,
        "end": end_date,
        "latitude": latitude,
        "longitude": longitude,
        "community": "ag",
        "parameters": params_list
    }
 
    response = requests.get(base_url, params=parameters)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Received status code {response.status_code}. Response text: {response.text}")
        return None
 
# Setting the start date manually and computing the end date
start_date = "20220501"
end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
 
config = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [
            18.9973,
            45.3394,
            96.34
        ]
    },
    "properties": {
        "parameter": {
            "T2M": {},
            "T2MDEW": {},
            "T2MWET": {},
            "TS": {},
            "T2M_RANGE": {},
            "T2M_MAX": {},
            "T2M_MIN": {},
            "ALLSKY_SFC_SW_DWN": {},
            "CLRSKY_SFC_SW_DWN": {},
            "ALLSKY_KT": {},
            "ALLSKY_SFC_LW_DWN": {},
            "ALLSKY_SFC_PAR_TOT": {},
            "CLRSKY_SFC_PAR_TOT": {},
            "ALLSKY_SFC_UVA": {},
            "ALLSKY_SFC_UVB": {},
            "ALLSKY_SFC_UV_INDEX": {}
        }
    },
    "header": {
        "title": "NASA/POWER CERES/MERRA2 Native Resolution Daily Data",
        "api": {
            "version": "v2.4.5",
            "name": "POWER Daily API"
        },
        "sources": [
            "flashflux",
            "ceres",
            "power",
            "merra2"
        ],
        "fill_value": -999,
        "start": start_date,
        "end": end_date
    }
}
 
temperature_data = fetch_nasa_power_data(config)
 
if temperature_data:
    # Define the "DB" folder path directly
    db_folder = "E:\\THPapp\\Energy\\DB"
 
    # Ensure the "DB" folder exists
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
 
    # Adjust the save path for the JSON file to be within the "DB" directory
    output_path = os.path.join(db_folder, "tempdatabase.json")
 
    # Save data to a JSON file:
    with open(output_path, "w") as outfile:
        json.dump(temperature_data, outfile, indent=4)
 
import subprocess
 
# Call the E:\THPapp\Energy\OneToRuleThemAll.py script
with open("E:\\THPapp\\Energy\\OneToRuleThemAll.py", "r") as file:
    exec(file.read())
 
 