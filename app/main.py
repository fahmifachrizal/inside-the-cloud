from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import dashboard, weather, gpm

app = FastAPI(title="Unified Weather Processor")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(dashboard.router)
app.include_router(weather.router, prefix="/api/weather", tags=["NOAA"])
app.include_router(gpm.router, prefix="/api/gpm", tags=["GPM"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)