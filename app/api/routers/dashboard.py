from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    # ... Paste the FULL HTML string from the previous "Updated app/main.py" response here ...
    # For brevity, I am referencing the HTML provided in the previous step.
    return """
<!DOCTYPE html>
    <html>
    <head>
        <title>Weather Dashboard</title>
        <style>
            body { margin: 0; padding: 0; font-family: monospace; display: flex; height: 100vh; overflow: hidden; }
            
            /* SIDEBAR */
            .sidebar {
                width: 40%;
                min-width: 350px;
                padding: 20px;
                background: #f8f8f8;
                border-right: 1px solid #ccc;
                overflow-y: auto;
                flex-shrink: 0;
                box-sizing: border-box;
            }

            /* MAIN CONTENT */
            .main-content {
                flex: 1;
                background: #222;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                overflow: hidden;
            }

            h2 { margin-top: 0; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
            fieldset { border: 1px solid #999; margin-bottom: 20px; padding: 15px; background: #fff; }
            legend { font-weight: bold; padding: 0 5px; background: #f8f8f8; }
            label { display: block; margin-top: 10px; font-weight: bold; font-size: 0.85em; color: #555; }
            input, select { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; border: 1px solid #ccc; }
            button { width: 100%; padding: 10px; margin-top: 15px; background: #ddd; border: 1px solid #999; cursor: pointer; font-weight: bold; font-family: monospace; }
            button:hover { background: #ccc; }
            button:disabled { opacity: 0.6; cursor: wait; }
            .coord-row { display: flex; gap: 10px; }
            .coord-row div { flex: 1; }

            /* FILE LIST */
            #file-list { height: 200px; overflow-y: auto; border: 1px solid #ccc; background: #fff; margin-top: 5px; }
            .file-item {
                padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #eee; font-size: 0.85em;
                direction: rtl; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }
            .file-item:hover { background: #eef; }
            .file-item.selected { background: #333; color: #fff; border-color: #333; }

            /* IMAGE */
            #result-img { width: 100%; height: 100%; object-fit: contain; display: none; }
            #placeholder { color: #666; font-size: 1.5em; }

            /* LOADING */
            .loading { position: absolute; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.7); color: white; display: none; flex-direction: column; align-items: center; justify-content: center; z-index: 10; }
            .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #fff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 15px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>

        <div class="sidebar">
            <h2>Unified Weather</h2>
            
            <fieldset>
                <legend>1. Global Bounds</legend>
                <div class="coord-row">
                    <div><label>Top Lat</label><input type="number" id="toplat" value="-5" step="0.1"></div>
                    <div><label>Bottom Lat</label><input type="number" id="bottomlat" value="-10" step="0.1"></div>
                </div>
                <div class="coord-row">
                    <div><label>Left Lon</label><input type="number" id="leftlon" value="105" step="0.1"></div>
                    <div><label>Right Lon</label><input type="number" id="rightlon" value="115" step="0.1"></div>
                </div>
            </fieldset>

            <fieldset>
                <legend>2. NOAA GFS (Internet)</legend>
                <label>Date (YYYYMMDD)</label>
                <input type="text" id="date" value="20251218">
                <button onclick="plotNOAA()">Download & Plot GFS</button>
            </fieldset>

            <fieldset>
                <legend>3. Local GPM (HDF5)</legend>
                <button onclick="refreshFiles()" style="margin-top:0; margin-bottom:5px;">Refresh List</button>
                <div id="file-list">Loading...</div>
                <input type="hidden" id="selected-file">
                <button onclick="plotGPM()">Plot Selected File</button>
            </fieldset>
        </div>

        <div class="main-content">
            <div id="placeholder">Select Data Source</div>
            <img id="result-img" />
            <div id="loading" class="loading"><div class="spinner"></div><div>PROCESSING DATA...</div></div>
        </div>

        <script>
            function setLoading(isLoading) {
                document.getElementById('loading').style.display = isLoading ? 'flex' : 'none';
                document.querySelectorAll('button').forEach(b => b.disabled = isLoading);
            }
            function getParams() {
                return {
                    top: document.getElementById('toplat').value,
                    bottom: document.getElementById('bottomlat').value,
                    left: document.getElementById('leftlon').value,
                    right: document.getElementById('rightlon').value,
                    date: document.getElementById('date').value,
                    file: document.getElementById('selected-file').value
                };
            }
            function showImage(url) {
                const img = document.getElementById('result-img');
                const ph = document.getElementById('placeholder');
                img.onload = () => { setLoading(false); img.style.display = 'block'; ph.style.display = 'none'; };
                img.onerror = () => { setLoading(false); alert("Error loading plot."); };
                img.src = url;
            }
            function plotNOAA() {
                setLoading(true);
                const p = getParams();
                showImage(`/api/weather/filter_fnl?date=${p.date}&hour=00&toplat=${p.top}&bottomlat=${p.bottom}&leftlon=${p.left}&rightlon=${p.right}&mode=image`);
            }
            function plotGPM() {
                const p = getParams();
                if(!p.file) return alert("Select a file first.");
                setLoading(true);
                showImage(`/api/gpm/plot?filename=${p.file}&toplat=${p.top}&bottomlat=${p.bottom}&leftlon=${p.left}&rightlon=${p.right}&ts=${Date.now()}`);
            }
            async function refreshFiles() {
                const div = document.getElementById('file-list');
                div.innerHTML = '<div style="padding:10px">Loading...</div>';
                try {
                    const res = await fetch('/api/gpm/files');
                    const files = await res.json();
                    div.innerHTML = '';
                    if(files.length === 0) div.innerHTML = '<div style="padding:10px">No files in app/data/</div>';
                    files.forEach(f => {
                        const item = document.createElement('div');
                        item.className = 'file-item';
                        item.innerText = f;
                        item.title = f;
                        item.onclick = () => {
                            document.querySelectorAll('.file-item').forEach(x => x.classList.remove('selected'));
                            item.classList.add('selected');
                            document.getElementById('selected-file').value = f;
                        };
                        div.appendChild(item);
                    });
                } catch(e) { div.innerHTML = 'Error listing files'; }
            }
            refreshFiles();
        </script>
    </body>
    </html>
    """