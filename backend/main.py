import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes.map_routes import router as map_router
from backend.routes.advisory_routes import router as advisory_router
from backend.routes.parcel_routes import router as parcel_router
from backend.routes.ai_routes import router as ai_router
from backend.routes.marketplace_routes import router as marketplace_router
from backend.routes.phases_routes import router as phases_router
from backend.services.data_store import consumer_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("local_ag")

app = FastAPI(
    title="Chicago Ag Connect API",
    description="Fresh Food Markets Directory & Backyard Garden Advisory Platform",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(map_router)
app.include_router(advisory_router)
app.include_router(parcel_router)
app.include_router(ai_router)
app.include_router(marketplace_router)
app.include_router(phases_router)

# Mount Static Assets
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health_check():
    from backend.config import SUPPORTED_STATES
    return {
        "status": "healthy",
        "service": "Chicago Ag Connect Consumer Platform",
        "loaded_locations": len(consumer_store._locations),
        "supported_states": SUPPORTED_STATES
    }
