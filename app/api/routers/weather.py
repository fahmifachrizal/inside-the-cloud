from fastapi import APIRouter, Query, Response, HTTPException
from app.services import noaa_service
from app.utils import plotting, formatting

router = APIRouter()

@router.get("/filter_fnl")
async def get_noaa_data(
    date: str = Query(...),
    hour: str = Query("00"),
    toplat: float = Query(...),
    bottomlat: float = Query(...),
    leftlon: float = Query(...),
    rightlon: float = Query(...),
    mode: str = Query("image"),
):
    bounds = {'top': toplat, 'bottom': bottomlat, 'left': leftlon, 'right': rightlon}
    
    try:
        # Service: Get Data
        lats, lons, data = await noaa_service.fetch_and_process_gfs(date, hour, bounds)
        
        if mode == "image":
            # Utils: Plot Data
            date_clean = formatting.format_pretty_date(date, hour)
            img_bytes = plotting.generate_heatmap(
                lats, lons, data, bounds, 
                "NOAA GFS (0.25°)", date_clean
            )
            return Response(content=img_bytes, media_type="image/png")
        else:
            return Response(content=b"Binary mode skipped", media_type="text/plain")

    except Exception as e:
        return Response(status_code=500, content=str(e), media_type="text/plain")