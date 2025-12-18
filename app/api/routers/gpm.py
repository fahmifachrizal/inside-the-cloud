from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import geojson
from geojson import Feature, FeatureCollection, MultiPolygon
import os
import struct

# --- IMPORTS FROM YOUR PROJECT STRUCTURE ---
from app.services import gpm_service
from app.utils import formatting, plotting 

router = APIRouter()

# Thresholds for rain intensity (mm/hr)
LEVELS = [0.5, 5.0, 10.0, 20.0]

# ==========================================
# 1. NEW VECTOR ENDPOINT (ROBUST)
# ==========================================
@router.get("/vector")
async def get_gpm_vector(
    filename: str,
    toplat: float,
    bottomlat: float,
    leftlon: float,
    rightlon: float
):
    try:
        file_path = f"app/data/{filename}"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # 1. OPEN DATASET
        try:
            # decode_times=False prevents "julian calendar" crashes
            ds = xr.open_dataset(file_path, engine='h5netcdf', group='Grid', decode_times=False)
        except OSError:
            # Fallback: Try opening root if 'Grid' group doesn't exist
            ds = xr.open_dataset(file_path, engine='h5netcdf', decode_times=False)

        # 2. IDENTIFY VARIABLES (Your Improved Logic)
        candidates = ['precipitationCal', 'precipitation', 'precip']
        var_name = next((v for v in candidates if v in ds), None)
        
        # Check coordinates dynamically (case-insensitive)
        lat_name = next((k for k in ds.coords if 'lat' in k.lower()), 'lat')
        lon_name = next((k for k in ds.coords if 'lon' in k.lower()), 'lon')

        if not var_name:
             raise HTTPException(status_code=500, detail=f"No rain variable found. Keys: {list(ds.keys())}")

        # 3. SLICE DATA
        # Select first time step [0]
        data = ds[var_name][0]

        # Use the detected coordinate names to slice
        subset = data.sel({
            lat_name: slice(bottomlat, toplat),
            lon_name: slice(leftlon, rightlon)
        })

        # 4. PREPARE FOR MATPLOTLIB
        # We need data in (lat, lon) format for contouring
        # GPM is usually (lon, lat) or (time, lon, lat).
        # subset.dims tells us the order. If it starts with 'lon', we transpose.
        if subset.dims[0].lower().startswith('lon'):
            precip = subset.values.T  # Transpose to get (Lat, Lon)
            lats = subset.coords[lat_name].values
            lons = subset.coords[lon_name].values
        else:
            precip = subset.values
            lats = subset.coords[lat_name].values
            lons = subset.coords[lon_name].values

        # 5. VECTORIZE (Matplotlib)
        plt.switch_backend('Agg')
        features = []
        
        for level in LEVELS:
            # Generate contours
            cs = plt.contour(lons, lats, precip, levels=[level, 99999])
            
            for collection in cs.collections:
                for path in collection.get_paths():
                    if len(path.vertices) < 3: continue
                    
                    coords = path.to_polygons()
                    if len(coords) > 0:
                        poly_coords = [c.tolist() for c in coords]
                        features.append(Feature(
                            geometry=MultiPolygon([poly_coords]),
                            properties={"level": level}
                        ))
        
        plt.clf()
        plt.close()
        ds.close()

        return JSONResponse(content=FeatureCollection(features))

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 2. EXISTING ENDPOINTS
# ==========================================

@router.get("/files")
async def list_files():
    return gpm_service.list_available_files()

@router.get("/plot")
async def plot_gpm_file(
    filename: str = Query(...),
    toplat: float = Query(...),
    bottomlat: float = Query(...),
    leftlon: float = Query(...),
    rightlon: float = Query(...),
):
    bounds = {'top': toplat, 'bottom': bottomlat, 'left': leftlon, 'right': rightlon}
    try:
        lats, lons, data = gpm_service.process_local_file(filename, bounds)
        date_clean = formatting.parse_gpm_filename(filename)
        img_bytes = plotting.generate_heatmap(
            lats, lons, data, bounds, 
            "GPM IMERG", date_clean
        )
        return Response(content=img_bytes, media_type="image/png")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(status_code=500, content=str(e), media_type="text/plain")
    
@router.get("/data")
async def get_gpm_data(
    filename: str = Query(...),
    toplat: float = Query(...),
    bottomlat: float = Query(...),
    leftlon: float = Query(...),
    rightlon: float = Query(...),
    threshold: float = Query(0.1, description="Minimum mm/hr to include"),
    format: str = Query("json", enum=["json", "bin"], description="Response format")
):
    bounds = {'top': toplat, 'bottom': bottomlat, 'left': leftlon, 'right': rightlon}
    try:
        lats, lons, vals, max_val = gpm_service._extract_cloud_arrays(filename, bounds, threshold)
        count = len(vals)

        if format == "bin":
            header = struct.pack('<If', count, max_val)
            body = lats.tobytes() + lons.tobytes() + vals.tobytes()
            return Response(content=header + body, media_type="application/octet-stream")
        else:
            return {
                "meta": {"count": count, "max_val": round(max_val, 2), "bounds": bounds},
                "lats": np.round(lats, 3).tolist(),
                "lons": np.round(lons, 3).tolist(),
                "vals": np.round(vals, 2).tolist()
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(status_code=500, content=str(e), media_type="text/plain")