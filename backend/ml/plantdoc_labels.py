"""
Map PlantDoc folder names → Chicago Ag Connect catalog keys.

Source: https://github.com/pratikkayal/PlantDoc-Dataset
"""
from __future__ import annotations

from typing import Dict, List

# Folder names are case-sensitive as shipped in the upstream repo.
PLANTDOC_FOLDER_TO_CATALOG: Dict[str, str] = {
    # Apple
    "Apple Scab Leaf": "apple_scab",
    "Apple leaf": "apple_healthy",
    "Apple rust leaf": "apple_cedar_rust",
    # Pepper
    "Bell_pepper leaf": "pepper_healthy",
    "Bell_pepper leaf spot": "pepper_bacterial_spot",
    # Corn
    "Corn Gray leaf spot": "corn_gray_leaf_spot",
    "Corn leaf blight": "corn_leaf_blight",
    "Corn rust leaf": "corn_common_rust",
    # Potato
    "Potato leaf early blight": "potato_early_blight",
    "Potato leaf late blight": "potato_late_blight",
    "Potato leaf": "potato_healthy",
    # Squash
    "Squash Powdery mildew leaf": "squash_powdery_mildew",
    # Strawberry
    "Strawberry leaf": "strawberry_healthy",
    # Tomato
    "Tomato Early blight leaf": "tomato_early_blight",
    "Tomato Septoria leaf spot": "tomato_septoria_leaf_spot",
    "Tomato leaf": "tomato_healthy",
    "Tomato leaf bacterial spot": "tomato_bacterial_spot",
    "Tomato leaf late blight": "tomato_late_blight",
    "Tomato leaf mosaic virus": "tomato_mosaic_virus",
    "Tomato leaf yellow virus": "tomato_yellow_leaf_curl",
    "Tomato two spotted spider mites leaf": "tomato_spider_mites",
    "Tomato mold leaf": "tomato_leaf_mold",
    # Grape
    "grape leaf": "grape_healthy",
    "grape leaf black rot": "grape_black_rot",
    # Other healthy / foliar classes useful for Chicago gardens
    "Blueberry leaf": "blueberry_healthy",
    "Cherry leaf": "cherry_healthy",
    "Peach leaf": "peach_healthy",
    "Raspberry leaf": "raspberry_healthy",
    "Soyabean leaf": "soybean_healthy",
}

# Alternate spellings / accidental renames sometimes seen in mirrors
PLANTDOC_FOLDER_ALIASES: Dict[str, str] = {
    "Soybean leaf": "soybean_healthy",
    "Tomato leaf yellow virus ": "tomato_yellow_leaf_curl",
}


def resolve_plantdoc_folder(folder_name: str) -> str | None:
    """Return catalog key for a PlantDoc class folder, or None if unmapped."""
    if folder_name in PLANTDOC_FOLDER_TO_CATALOG:
        return PLANTDOC_FOLDER_TO_CATALOG[folder_name]
    if folder_name in PLANTDOC_FOLDER_ALIASES:
        return PLANTDOC_FOLDER_ALIASES[folder_name]
    # Soft match: strip + casefold
    soft = {k.strip().casefold(): v for k, v in PLANTDOC_FOLDER_TO_CATALOG.items()}
    soft.update({k.strip().casefold(): v for k, v in PLANTDOC_FOLDER_ALIASES.items()})
    return soft.get(folder_name.strip().casefold())


def mapped_catalog_keys() -> List[str]:
    return sorted(set(PLANTDOC_FOLDER_TO_CATALOG.values()))
