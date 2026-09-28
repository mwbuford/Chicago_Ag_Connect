from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. Vision Plant & Disease Classifier Models
# ==========================================

class DiseaseRemedy(BaseModel):
    organic_controls: List[str] = Field(default_factory=list, description="Immediate organic remedies (e.g. neem oil, copper fungicide, pruning)")
    cultural_prevention: List[str] = Field(default_factory=list, description="Long-term cultural practices (e.g. drip irrigation, crop rotation)")
    safe_for_pollinators: bool = True
    severity_level: str = "Moderate" # "Low", "Moderate", "High / Urgent"

class PlantDiagnosisResult(BaseModel):
    plant_species: str = Field(..., description="Predicted plant species (e.g. Tomato, Apple, Corn, Grape, Pepper)")
    condition_name: str = Field(..., description="Identified disease or condition (e.g. Early Blight, Powdery Mildew, Healthy)")
    condition_category: str = Field(..., description="Fungal, Bacterial, Viral, Pest / Insect, or Healthy")
    confidence: float = Field(..., description="Model prediction confidence score between 0.0 and 1.0")
    top_predictions: List[Dict[str, Any]] = Field(default_factory=list, description="Top-k class probabilities")
    symptoms: List[str] = Field(default_factory=list, description="Key symptoms matching this visual pathology")
    organic_remedy: DiseaseRemedy
    regional_context_note: Optional[str] = None
    inference_time_ms: float = 0.0


# ==========================================
# 2. Agronomic SLM (Small Language Model)
# ==========================================

class AgronomyChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Text content of the message")

class AgronomySLMRequest(BaseModel):
    prompt: str = Field(..., description="User query or question for the agronomic SLM")
    state: Optional[str] = Field(None, description="Two-letter state code e.g. IL, VA, TX, CA")
    county: Optional[str] = Field(None, description="County name e.g. Cook, Albemarle, Travis")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    mode: str = Field("gardener", description="gardener | homesteader | small_farm")
    conversation_history: List[AgronomyChatMessage] = Field(default_factory=list)
    max_new_tokens: int = 350
    temperature: float = 0.7

class AgronomySLMResponse(BaseModel):
    response: str = Field(..., description="Agronomic SLM generated answer")
    model_name: str = Field("BackyardAg-Agronomy-SLM-v1", description="Name of the custom model")
    context_injected: Dict[str, Any] = Field(default_factory=dict, description="Agronomic & climate parameters injected into inference")
    inference_time_ms: float = 0.0
    sources_referenced: List[str] = Field(default_factory=list)
