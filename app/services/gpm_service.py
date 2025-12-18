import os
import xarray as xr
import numpy as np
from app.core.config import DATA_DIR

def process_local_file(filename, bounds):
    """
    Opens HDF5, crops to bounds, returns (lats, lons, data).
    """
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError("GPM File not found")

    # 1. Open
    try:
        ds = xr.open_dataset(file_path, group='Grid', engine='h5netcdf', decode_times=False)
    except:
        ds = xr.open_dataset(file_path, engine='h5netcdf', decode_times=False)

    # 2. Identify Variables
    candidates = ['precipitationCal', 'precipitation', 'precip']
    var_name = next((v for v in candidates if v in ds), None)
    if not var_name: raise ValueError("Variable not found in GPM file")

    lat_name = next((k for k in ds.coords if 'lat' in k.lower()), 'lat')
    lon_name = next((k for k in ds.coords if 'lon' in k.lower()), 'lon')

    # 3. Crop (Optimization)
    lat_slice = slice(min(bounds['bottom'], bounds['top']), max(bounds['bottom'], bounds['top']))
    lon_slice = slice(min(bounds['left'], bounds['right']), max(bounds['left'], bounds['right']))
    
    try:
        ds_cropped = ds.sel({lat_name: lat_slice, lon_name: lon_slice})
        if ds_cropped[var_name].size == 0: ds_cropped = ds # Fallback
    except:
        ds_cropped = ds

    # 4. Extract Arrays
    data = ds_cropped[var_name].squeeze().values
    lats = ds_cropped[lat_name].values
    lons = ds_cropped[lon_name].values

    # Transpose if (lon, lat)
    if data.shape == (len(lons), len(lats)):
        data = data.T 

    ds.close()
    return lats, lons, data

def list_available_files():
    if not os.path.exists(DATA_DIR): return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith(('.HDF5', '.nc', '.nc4'))]