import os
import time
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms

from backend.models.plant_disease_catalog import PLANT_DISEASE_CATALOG, CLASS_NAMES, NUM_CLASSES
from backend.models.ai_models import PlantDiagnosisResult, DiseaseRemedy
from backend.ml.vision_model_arch import PlantPathologyNet

logger = logging.getLogger("vision_service")

class PlantVisionClassifierService:
    def __init__(self, weights_path: Optional[str] = None):
        self.device = torch.device("cpu")
        self.weights_path = weights_path or str(Path(__file__).resolve().parent.parent / "ml" / "weights" / "plant_disease_model.pt")
        self.model: Optional[PlantPathologyNet] = None
        self.class_names: List[str] = list(CLASS_NAMES)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self._load_model()

    def _load_model(self):
        try:
            num_classes = NUM_CLASSES
            checkpoint = None
            self.class_names = list(CLASS_NAMES)
            if os.path.exists(self.weights_path):
                checkpoint = torch.load(self.weights_path, map_location=self.device)
                num_classes = int(checkpoint.get("num_classes", NUM_CLASSES))
                ckpt_names = checkpoint.get("class_names")
                if ckpt_names:
                    self.class_names = list(ckpt_names)
                if list(self.class_names) != list(CLASS_NAMES):
                    logger.warning(
                        "Checkpoint class_names differ from current catalog. "
                        "Retrain with: PYTHONPATH=. python backend/ml/train_vision_classifier.py"
                    )

            self.model = PlantPathologyNet(num_classes=num_classes, pretrained=False).to(self.device)
            if checkpoint is not None:
                if "model_state_dict" in checkpoint:
                    self.model.load_state_dict(checkpoint["model_state_dict"])
                else:
                    self.model.load_state_dict(checkpoint)
                logger.info(f"Loaded custom PlantPathologyNet weights from {self.weights_path}")
            else:
                logger.warning(f"No weights found at {self.weights_path}. Using initialized architecture.")
            self.model.eval()
        except Exception as e:
            logger.error(f"Error loading vision model: {e}")
            self.model = None
            self.class_names = list(CLASS_NAMES)

    def predict_image(
        self,
        image_bytes: bytes,
        state: Optional[str] = None,
        county: Optional[str] = None
    ) -> PlantDiagnosisResult:
        start_time = time.time()

        # Load and convert image to RGB PIL
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_tensor = self.transform(image).unsqueeze(0).to(self.device)

        if self.model is None:
            self._load_model()

        with torch.no_grad():
            if self.model is not None:
                logits = self.model(img_tensor)
                probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()
            else:
                probs = np.ones(len(self.class_names)) / max(len(self.class_names), 1)

        labels = self.class_names or list(CLASS_NAMES)
        top_k_indices = np.argsort(probs)[::-1][:3]
        top_idx = int(top_k_indices[0])
        pred_class = labels[top_idx] if top_idx < len(labels) else CLASS_NAMES[0]
        confidence = float(probs[top_idx])

        # Get catalog details
        catalog_entry = PLANT_DISEASE_CATALOG.get(pred_class, {
            "plant_species": "Garden Plant",
            "condition_name": "Unknown Condition",
            "condition_category": "Fungal",
            "symptoms": ["Visible foliar irregularities detected"],
            "organic_remedy": {
                "organic_controls": ["Apply organic neem oil or copper fungicide"],
                "cultural_prevention": ["Water at soil level and prune affected leaves"],
                "safe_for_pollinators": True,
                "severity_level": "Moderate"
            }
        })

        top_predictions = []
        for rank, idx in enumerate(top_k_indices):
            c_name = labels[int(idx)] if int(idx) < len(labels) else CLASS_NAMES[0]
            c_entry = PLANT_DISEASE_CATALOG.get(c_name, {})
            top_predictions.append({
                "rank": rank + 1,
                "class_key": c_name,
                "plant_species": c_entry.get("plant_species", c_name),
                "condition_name": c_entry.get("condition_name", c_name),
                "confidence": round(float(probs[idx]), 4)
            })

        # Format regional context note if state/county given
        reg_note = None
        if state:
            st_upper = state.upper()
            from backend.services.advisory_engine import STATE_EXTENSIONS
            ext = STATE_EXTENSIONS.get(st_upper, {})
            pest_watch = ext.get("pest_watch", [])
            if any(p.lower() in catalog_entry["condition_name"].lower() for p in pest_watch):
                reg_note = f"⚠️ High alert: {catalog_entry['condition_name']} is currently on the active pest & pathogen watchlist for {county or state}."
            else:
                reg_note = f"Region verified for {st_upper}. Common in {ext.get('ecoregion', 'temperate')} climates."

        raw_remedy = catalog_entry["organic_remedy"]
        remedy = DiseaseRemedy(
            organic_controls=raw_remedy.get("organic_controls", []),
            cultural_prevention=raw_remedy.get("cultural_prevention", []),
            safe_for_pollinators=raw_remedy.get("safe_for_pollinators", True),
            severity_level=raw_remedy.get("severity_level", "Moderate")
        )

        inference_time_ms = round((time.time() - start_time) * 1000, 2)

        return PlantDiagnosisResult(
            plant_species=catalog_entry["plant_species"],
            condition_name=catalog_entry["condition_name"],
            condition_category=catalog_entry["condition_category"],
            confidence=round(confidence, 4),
            top_predictions=top_predictions,
            symptoms=catalog_entry["symptoms"],
            organic_remedy=remedy,
            regional_context_note=reg_note,
            inference_time_ms=inference_time_ms
        )

# Global Singleton instance
vision_service = PlantVisionClassifierService()
