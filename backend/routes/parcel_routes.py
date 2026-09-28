from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Query
from fastapi.responses import Response
from backend.models.parcel import PropertyAnalysisResponse
from backend.services.vision_parcelizer import analyze_property_aerial
from backend.services.shapefile_exporter import (
    register_analysis,
    get_analysis,
    generate_shapefile_zip_bytes,
    generate_geojson_bytes
)

router = APIRouter(prefix="/api/parcels", tags=["AI Land Parcelization"])

@router.post("/analyze-upload", response_model=PropertyAnalysisResponse)
async def analyze_uploaded_aerial(
    file: UploadFile = File(...),
    lat: float = Form(40.1100),
    lon: float = Form(-88.2050),
    acres: float = Form(45.0)
):
    """
    Accepts an uploaded aerial/drone photo, performs multi-class land segmentation,
    calculates slope overlays, and produces georeferenced parcel polygons.
    """
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    analysis = await analyze_property_aerial(
        image_bytes=content,
        center_lat=lat,
        center_lon=lon,
        approx_acres=acres
    )
    register_analysis(analysis)
    return analysis

@router.post("/analyze-demo", response_model=PropertyAnalysisResponse)
async def analyze_demo_property(
    lat: float = Query(40.1100, description="Center latitude"),
    lon: float = Query(-88.2050, description="Center longitude"),
    acres: float = Query(50.0, description="Property size in acres")
):
    """
    Generates a simulated instant aerial property parcelization analysis 
    for rapid testing without needing a local image file.
    """
    analysis = await analyze_property_aerial(
        image_bytes=b"DEMO_AERIAL_BYTES",
        center_lat=lat,
        center_lon=lon,
        approx_acres=acres
    )
    register_analysis(analysis)
    return analysis

@router.get("/export/{analysis_id}/shapefile")
def export_shapefile(analysis_id: str):
    """Download ESRI Shapefile (.zip) bundle containing .shp, .shx, .dbf, .prj."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis session expired or not found")

    zip_bytes = generate_shapefile_zip_bytes(analysis)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=local_ag_parcel_{analysis_id}.zip"
        }
    )

@router.get("/export/{analysis_id}/geojson")
def export_geojson(analysis_id: str):
    """Download RFC 7946 GeoJSON FeatureCollection."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis session expired or not found")

    geojson_bytes = generate_geojson_bytes(analysis)
    return Response(
        content=geojson_bytes,
        media_type="application/geo+json",
        headers={
            "Content-Disposition": f"attachment; filename=local_ag_parcel_{analysis_id}.geojson"
        }
    )
