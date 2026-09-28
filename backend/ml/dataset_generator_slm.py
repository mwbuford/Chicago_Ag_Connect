import json
import os
from pathlib import Path
from typing import List, Dict, Any

from backend.models.plant_disease_catalog import PLANT_DISEASE_CATALOG

def load_data_sources():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    with open(data_dir / "crop_library.json", "r", encoding="utf-8") as f:
        crop_lib = json.load(f)
    with open(data_dir / "state_extensions.json", "r", encoding="utf-8") as f:
        state_ext = json.load(f)
    return crop_lib, state_ext

def generate_agronomy_slm_dataset(output_path: str = "backend/ml/data/agronomy_qa_dataset.jsonl") -> int:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []
    crop_library, state_extensions = load_data_sources()

    # 1. Generate State-Specific Soil & Climate Q&A
    for state_code, ext in state_extensions.items():
        state_name = ext.get("ecoregion", "Temperate").title()
        soil_type = ext.get("soil_profile", {}).get("texture", "Silt Loam")
        ph_range = ext.get("soil_profile", {}).get("ph_range", "6.0 - 7.0")
        pest_watch = ext.get("pest_watch", [])
        natives = ext.get("native_species", [])

        # Question 1: Soil Amendment
        records.append({
            "instruction": f"How do I prepare and amend garden soil in {state_code}?",
            "input": f"Location: {state_code}, Native Soil: {soil_type}, Native pH: {ph_range}",
            "output": f"In {state_code}, the predominant native soil texture is {soil_type} with a typical pH range of {ph_range}. To optimize for vegetable gardening, incorporate 2-3 inches of well-aged organic compost or leaf mold into the top 6-8 inches of soil. If your soil has heavy clay characteristics, avoid synthetic tilling when wet and add coarse organic matter. For raised beds, a blend of 50% topsoil, 30% organic compost, and 20% perlite or pine bark provides ideal drainage and nutrient retention.",
            "topic": "soil_amendment",
            "state": state_code
        })

        # Question 2: Native Plants
        if natives:
            native_names = [n["common_name"] for n in natives]
            first_native = natives[0]
            records.append({
                "instruction": f"What native plants are best for supporting local pollinators in {state_code}?",
                "input": f"Location: {state_code}, Ecoregion: {ext.get('ecoregion', 'General')}",
                "output": f"Top recommended native species for {state_code} include {', '.join(native_names)}. Specifically, {first_native['common_name']} ({first_native.get('botanical_name', '')}) is exceptionally beneficial because it provides {first_native.get('ecoregion_benefits', 'high ecological value')}. It thrives in {first_native.get('sun_and_soil', 'standard garden conditions')} with {first_native.get('water_needs', 'moderate')} water requirements and serves well as {first_native.get('best_garden_use', 'pollinator border')}.",
                "topic": "native_plants",
                "state": state_code
            })

        # Question 3: Regional Pests
        if pest_watch:
            records.append({
                "instruction": f"What pests and diseases should gardeners watch out for in {state_code}?",
                "input": f"Location: {state_code}",
                "output": f"Gardeners in {state_code} should actively monitor for: {', '.join(pest_watch)}. Practice proactive organic control by inspecting the undersides of leaves weekly, employing floating row covers early in the season, using drip irrigation to keep foliage dry, and applying organic cold-pressed neem oil or Bacillus thuringiensis (Bt) at early signs of infestation.",
                "topic": "pest_management",
                "state": state_code
            })

    # 2. Generate Crop-Specific Growing Guides Q&A
    for crop in crop_library:
        crop_id = crop.get("crop_id", "crop")
        name = crop.get("crop_name", "Vegetable")
        sun = crop.get("sun_requirement", "Full Sun")
        depth = crop.get("container_depth_inches", 12)
        diff = crop.get("difficulty", "Easy")
        pro_tip = crop.get("backyard_pro_tip", "Water consistently at the base.")
        indoor = crop.get("indoor_seed_weeks_before_last_frost")
        transplant = crop.get("outdoor_transplant_weeks_after_last_frost")

        indoor_str = f"Start seeds indoors {indoor[0]}-{indoor[1]} weeks before your last spring frost. " if indoor else ""
        transplant_str = f"Transplant outdoors {transplant[0]}-{transplant[1]} weeks after last frost once soil warms. " if transplant else ""

        records.append({
            "instruction": f"How do I successfully grow {name} in my backyard garden?",
            "input": f"Crop: {name}, Difficulty: {diff}, Sun: {sun}",
            "output": f"{name} is rated as {diff} for home gardeners. It requires {sun} and a root container depth of at least {depth} inches. {indoor_str}{transplant_str}Pro-Tip: {pro_tip}",
            "topic": "crop_care",
            "crop": crop_id
        })

    # 3. Generate Disease & Pathology Organic Remedies Q&A
    for disease_id, d in PLANT_DISEASE_CATALOG.items():
        plant = d["plant_species"]
        cond = d["condition_name"]
        remedy = d["organic_remedy"]
        symptoms = d["symptoms"]

        records.append({
            "instruction": f"My {plant} leaves have symptoms of {cond}. How do I treat it organically?",
            "input": f"Plant: {plant}, Condition: {cond}, Symptoms: {'; '.join(symptoms)}",
            "output": f"For {cond} on {plant}, immediate organic control steps include: {'; '.join(remedy['organic_controls'])}. "
                      f"To prevent recurrence long-term: {'; '.join(remedy['cultural_prevention'])}. "
                      f"Severity level is rated as {remedy['severity_level']}. (Safe for pollinators: {'Yes' if remedy['safe_for_pollinators'] else 'Exercise Caution'}).",
            "topic": "disease_remedy",
            "disease": disease_id
        })

    # Write out JSONL file
    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    return len(records)

if __name__ == "__main__":
    count = generate_agronomy_slm_dataset()
    print(f"Generated {count} agronomic instructional Q&A pairs in backend/ml/data/agronomy_qa_dataset.jsonl")
