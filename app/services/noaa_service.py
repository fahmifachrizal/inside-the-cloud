import os
import httpx
import numpy as np
import xarray as xr
from app.core.config import TEMP_DIR

async def fetch_and_process_gfs(date, hour, bounds):
    """
    Downloads GFS GRIB file and returns (lats, lons, data) arrays.
    """
    base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl"
    dir_path = f"/gfs.{date}/{hour}/atmos"
    file_name = f"gfs.t{hour}z.pgrb2.0p25.anl"
    
    params = {
        "dir": dir_path, "file": file_name, "var_PRATE": "on", 
        "subregion": "", "toplat": bounds['top'], "leftlon": bounds['left'], 
        "rightlon": bounds['right'], "bottomlat": bounds['bottom'],
    }
    
    tmp_file = os.path.join(TEMP_DIR, f"gfs_{date}_{hour}.grib2")

    # 1. Download
    async with httpx.AsyncClient() as client:
        resp = await client.get(base_url, params=params, timeout=90.0)
        if resp.status_code != 200: 
            raise Exception(f"NOAA Upstream Error: {resp.status_code}")
        with open(tmp_file, "wb") as f: 
            f.write(resp.content)

    # 2. Process
    try:
        ds = xr.open_dataset(tmp_file, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': 'prate'}})
        
        # Convert units (kg/m^2/s -> mm/hr)
        data = ds['prate'].values * 3600
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        
        ds.close()
        return lats, lons, data
    finally:
        if os.path.exists(tmp_file): 
            os.remove(tmp_file)