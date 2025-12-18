import os
import struct
import io
import httpx
import numpy as np
import xarray as xr
import matplotlib
# Set backend to 'Agg' to render images without a display (required for Docker)
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NOAA GRIB Processor")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. The Dashboard Endpoint ---
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GRIB Weather API Dashboard</title>
        <style>
            body { font-family: -apple-system, system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f9; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            .row { display: flex; gap: 10px; }
            .col { flex: 1; }
            button { background: #0070f3; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%; margin-top: 10px; }
            button:hover { background: #0051a2; }
            #result-area { margin-top: 20px; text-align: center; min-height: 200px; border: 2px dashed #ddd; display: flex; align-items: center; justify-content: center; background: #fff; }
            img { max-width: 100%; height: auto; }
            pre { text-align: left; background: #eee; padding: 10px; overflow: auto; width: 100%; }
        </style>
    </head>
    <body>
        <h1>🌦️ GRIB Processing Dashboard</h1>
        <div class="card">
            <div class="form-group">
                <label>Date (YYYYMMDD)</label>
                <input type="text" id="date" value="20251217">
            </div>
            
            <div class="row">
                <div class="col"><div class="form-group"><label>Top Lat</label><input type="number" id="toplat" value="-5" step="0.1"></div></div>
                <div class="col"><div class="form-group"><label>Bottom Lat</label><input type="number" id="bottomlat" value="-8" step="0.1"></div></div>
            </div>
            <div class="row">
                <div class="col"><div class="form-group"><label>Left Lon</label><input type="number" id="leftlon" value="105" step="0.1"></div></div>
                <div class="col"><div class="form-group"><label>Right Lon</label><input type="number" id="rightlon" value="115" step="0.1"></div></div>
            </div>

            <div class="form-group">
                <label>Output Mode</label>
                <select id="mode">
                    <option value="image">Image (PNG Plot)</option>
                    <option value="binary">Binary Stream (Float32)</option>
                </select>
            </div>

            <button onclick="fetchData()">Generate Request</button>
        </div>

        <div id="result-area">
            <span style="color: #888;">Result will appear here...</span>
        </div>

        <script>
            async function fetchData() {
                const resultArea = document.getElementById('result-area');
                resultArea.innerHTML = 'Loading from NOAA... (This takes 5-10s)';
                
                const date = document.getElementById('date').value;
                const toplat = document.getElementById('toplat').value;
                const bottomlat = document.getElementById('bottomlat').value;
                const leftlon = document.getElementById('leftlon').value;
                const rightlon = document.getElementById('rightlon').value;
                const mode = document.getElementById('mode').value;

                // Construct URL
                const url = `/api/weather/filter_fnl?date=${date}&hour=00&toplat=${toplat}&bottomlat=${bottomlat}&leftlon=${leftlon}&rightlon=${rightlon}&mode=${mode}`;

                try {
                    const response = await fetch(url);
                    
                    if (!response.ok) {
                        const err = await response.text();
                        throw new Error(err);
                    }

                    if (mode === 'image') {
                        const blob = await response.blob();
                        const imgUrl = URL.createObjectURL(blob);
                        resultArea.innerHTML = `<img src="${imgUrl}" alt="Weather Plot" />`;
                    } else {
                        const buffer = await response.arrayBuffer();
                        const view = new DataView(buffer);
                        const width = view.getUint32(0, true);
                        const height = view.getUint32(4, true);
                        resultArea.innerHTML = `
                            <pre>Binary Data Received!
Grid Size: ${width} x ${height}
Total Bytes: ${buffer.byteLength}
                            </pre>`;
                    }
                } catch (e) {
                    resultArea.innerHTML = `<div style="color:red; padding:10px;">Error: ${e.message}</div>`;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- 2. The Main Processing Endpoint ---
@app.get("/api/weather/filter_fnl")
async def get_weather_data(
    date: str = Query(..., min_length=8, max_length=8),
    hour: str = Query("00"),
    toplat: float = Query(-5.0),
    bottomlat: float = Query(-8.0),
    leftlon: float = Query(105.0),
    rightlon: float = Query(115.0),
    mode: str = Query("binary", enum=["binary", "image"]), # New Param
):
    base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_fnl.pl"
    dir_path = f"/gdas.{date}/{hour}/atmos"
    file_name = f"gdas.t{hour}z.pgrb2.1p00.anl"
    
    params = {
        "dir": dir_path,
        "file": file_name,
        "var_PRATE": "on",
        "subregion": "",
        "toplat": toplat,
        "leftlon": leftlon,
        "rightlon": rightlon,
        "bottomlat": bottomlat,
    }

    tmp_file = f"/tmp/weather_{date}_{hour}.grib2"

    try:
        # Download
        async with httpx.AsyncClient() as client:
            resp = await client.get(base_url, params=params, timeout=60.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="NOAA Error")
            with open(tmp_file, "wb") as f:
                f.write(resp.content)

        # Process
        try:
            ds = xr.open_dataset(tmp_file, engine='cfgrib', backend_kwargs={'filter_by_keys': {'shortName': 'prate'}})
        except Exception:
            raise HTTPException(status_code=500, detail="Invalid GRIB data received")

        rain_data = ds['prate'].values * 3600 # Convert to mm/hr
        rain_data = np.nan_to_num(rain_data, nan=0.0)
        
        # --- MODE SWITCHING ---
        
        # A. Image Mode
        if mode == "image":
            # Plot using Matplotlib
            fig = plt.figure(figsize=(10, 6))
            ax = plt.axes()
            
            # extent=[left, right, bottom, top]
            # Note: GRIB often returns lat sorted High->Low. Imshow needs care.
            im = ax.imshow(
                rain_data, 
                extent=[float(ds.longitude.min()), float(ds.longitude.max()), float(ds.latitude.min()), float(ds.latitude.max())],
                origin='upper', 
                cmap='jet',
                aspect='auto'
            )
            plt.colorbar(im, label='Precipitation (mm/hr)')
            plt.title(f"Rainfall: {date} (Hour {hour}z)")
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            ds.close()
            
            return Response(content=buf.getvalue(), media_type="image/png")

        # B. Binary Mode (Original)
        else:
            height, width = rain_data.shape
            lats = ds['latitude'].values
            lons = ds['longitude'].values
            
            header = struct.pack(
                '<2I4f', 
                width, height, 
                float(lats.min()), float(lats.max()), 
                float(lons.min()), float(lons.max())
            )
            body = rain_data.astype(np.float32).tobytes()
            ds.close()
            return Response(content=header + body, media_type="application/octet-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)