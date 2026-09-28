import io
import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.models.ai_models import (
    PlantDiagnosisResult,
    AgronomySLMRequest,
    AgronomySLMResponse
)
from backend.models.plant_disease_catalog import NUM_CLASSES
from backend.services.vision_classifier import vision_service
from backend.services.agronomy_slm_service import agronomy_slm_service

logger = logging.getLogger("ai_routes")

router = APIRouter(prefix="/api/ai", tags=["Custom AI Models"])

@router.post("/diagnose", response_model=PlantDiagnosisResult)
async def diagnose_plant_leaf(
    image: UploadFile = File(..., description="Plant leaf or pathology photo"),
    state: Optional[str] = Form("IL", description="Two-letter state code"),
    county: Optional[str] = Form(None, description="County name")
):
    """
    Model 1: Custom Plant & Disease Vision Classifier (PlantPathologyNet).
    Analyzes an uploaded leaf image, predicts plant species and disease condition,
    and returns immediate organic remedies and cultural prevention practices.
    """
    try:
        contents = await image.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty image file provided.")

        result = vision_service.predict_image(
            image_bytes=contents,
            state=state,
            county=county
        )
        return result
    except Exception as e:
        logger.error(f"Error during plant diagnosis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Vision model diagnosis failed: {str(e)}")

@router.post("/agronomy-slm", response_model=AgronomySLMResponse)
async def ask_agronomy_slm(req: AgronomySLMRequest):
    """
    Model 4: Domain-Specific Agronomic Small Language Model (LocalAg-Agronomy-SLM-v1).
    Processes garden queries with parametric context injection (hardiness zones,
    frost dates, soil textures, and regional pest watchlists).
    """
    try:
        if not req.prompt or not req.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

        response = agronomy_slm_service.generate_response(req)
        return response
    except Exception as e:
        logger.error(f"Error in Agronomy SLM generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agronomy SLM inference failed: {str(e)}")

@router.get("/status")
def get_ai_models_status():
    """
    Reports status, active weights, and capabilities of all custom in-house AI models.
    """
    has_weights = vision_service.model is not None
    return {
        "status": "online",
        "models": {
            "model_1_vision": {
                "name": "PlantPathologyNet-v2-MobileNet",
                "type": "MobileNetV2 transfer learning / PlantDoc fine-tuned",
                "classes_count": len(getattr(vision_service, "class_names", [])) or NUM_CLASSES,
                "dataset": "PlantDoc (pratikkayal/PlantDoc-Dataset)",
                "device": str(vision_service.device),
                "loaded": has_weights
            },
            "model_4_agronomy_slm": {
                "name": "BackyardAg-Agronomy-SLM-v2",
                "type": "Domain-Specific Agronomic Small Language Model",
                "modes": ["gardener", "homesteader", "small_farm"],
                "knowledge_vectors_count": len(agronomy_slm_service.knowledge_base),
                "supported_states_count": 52
            }
        }
    }
