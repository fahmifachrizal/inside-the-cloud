from fastapi import APIRouter, Query, Response, HTTPException
from app.services import gpm_service
from app.utils import plotting, formatting

router = APIRouter()

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
        # Service: Get Data
        lats, lons, data = gpm_service.process_local_file(filename, bounds)
        
        # Utils: Plot Data
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