import io
import zipfile
import json
import shapefile
from typing import Dict, Any
from backend.models.parcel import PropertyAnalysisResponse
from backend.config import PROCESSED_DATA_DIR

# WGS84 standard PRJ definition for GIS software (QGIS, ArcGIS, etc.)
WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
)

# In-memory registry of analyses for instant download
ANALYSIS_CACHE: Dict[str, PropertyAnalysisResponse] = {}

def register_analysis(analysis: PropertyAnalysisResponse):
    ANALYSIS_CACHE[analysis.analysis_id] = analysis

def get_analysis(analysis_id: str) -> PropertyAnalysisResponse:
    return ANALYSIS_CACHE.get(analysis_id)

def generate_shapefile_zip_bytes(analysis: PropertyAnalysisResponse) -> bytes:
    """
    Generates a zipped ESRI Shapefile bundle (.shp, .shx, .dbf, .prj) from the analysis zones.
    """
    shp_buffer = io.BytesIO()
    shx_buffer = io.BytesIO()
    dbf_buffer = io.BytesIO()

    # Initialize shapefile writer (Polygon type)
    with shapefile.Writer(shp=shp_buffer, shx=shx_buffer, dbf=dbf_buffer) as w:
        w.field("ZONE_ID", "C", size=20)
        w.field("CLASS", "C", size=25)
        w.field("ACRES", "N", decimal=2)
        w.field("SLOPE_PCT", "N", decimal=1)
        w.field("SOIL_TYPE", "C", size=50)
        w.field("REC_USE", "C", size=100)

        for zone in analysis.detected_zones:
            coords = zone.geojson_geometry["coordinates"][0]
            # pyshp expects list of [x, y] coordinates
            w.poly([coords])
            w.record(
                ZONE_ID=zone.id,
                CLASS=zone.land_class.value,
                ACRES=zone.area_acres,
                SLOPE_PCT=zone.avg_slope_percent,
                SOIL_TYPE=str(zone.soil_type or "Loam"),
                REC_USE=zone.recommended_use[:99]
            )

    # Package into ZIP archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"local_ag_parcel_{analysis.analysis_id}.shp", shp_buffer.getvalue())
        zf.writestr(f"local_ag_parcel_{analysis.analysis_id}.shx", shx_buffer.getvalue())
        zf.writestr(f"local_ag_parcel_{analysis.analysis_id}.dbf", dbf_buffer.getvalue())
        zf.writestr(f"local_ag_parcel_{analysis.analysis_id}.prj", WGS84_PRJ)
        # Also include JSON summary report in the zip bundle
        summary = {
            "analysis_id": analysis.analysis_id,
            "total_acres": analysis.total_acres,
            "zoning_breakdown": analysis.zoning_breakdown,
            "slope_summary": analysis.slope_summary,
            "agronomic_recommendations": analysis.agronomic_recommendations
        }
        zf.writestr("PARCEL_SUMMARY_REPORT.json", json.dumps(summary, indent=2))

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def generate_geojson_bytes(analysis: PropertyAnalysisResponse) -> bytes:
    """
    Generates standard RFC 7946 GeoJSON FeatureCollection for the analysis zones.
    """
    features = []
    for zone in analysis.detected_zones:
        features.append({
            "type": "Feature",
            "id": zone.id,
            "geometry": zone.geojson_geometry,
            "properties": {
                "zone_id": zone.id,
                "land_class": zone.land_class.value,
                "label": zone.label,
                "area_acres": zone.area_acres,
                "avg_slope_percent": zone.avg_slope_percent,
                "soil_type": zone.soil_type,
                "recommended_use": zone.recommended_use,
                "color": zone.color_hex
            }
        })

    geojson_obj = {
        "type": "FeatureCollection",
        "properties": {
            "analysis_id": analysis.analysis_id,
            "total_acres": analysis.total_acres,
            "slope_summary": analysis.slope_summary,
            "zoning_breakdown": analysis.zoning_breakdown,
            "recommendations": analysis.agronomic_recommendations
        },
        "features": features
    }

    return json.dumps(geojson_obj, indent=2).encode("utf-8")
