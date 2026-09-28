import json
import logging
from pathlib import Path
from typing import List, Optional

from backend.models.phases import LearningPath, ResourceModule, ResourceHubResponse, SubPath

logger = logging.getLogger("resource_hub")

PATHS_FILE = Path(__file__).resolve().parent.parent / "data" / "learning_paths.json"


class ResourceHubService:
    """Phase 6: Homestead & farm learning paths with checklists and AI integration."""

    def __init__(self):
        self._paths: List[LearningPath] = []
        self._load()

    def _load(self):
        if not PATHS_FILE.exists():
            logger.warning("learning_paths.json not found")
            return
        with open(PATHS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._paths = []
        for p in raw:
            # modules can be a dict (keyed by module_id) or a list
            raw_modules = p.get("modules", {})
            if isinstance(raw_modules, dict):
                modules = [ResourceModule(**m) for m in raw_modules.values()]
            else:
                modules = [ResourceModule(**m) for m in raw_modules]

            sub_paths = [SubPath(**sp) for sp in p.get("sub_paths", [])]

            self._paths.append(LearningPath(
                path_id=p["path_id"],
                title=p["title"],
                description=p["description"],
                icon=p["icon"],
                target_audience=p["target_audience"],
                agronomy_mode=p["agronomy_mode"],
                modules=modules,
                total_modules=len(modules),
                sub_paths=sub_paths,
                cta_label=p.get("cta_label"),
                cta_action=p.get("cta_action")
            ))
        logger.info(f"Loaded {len(self._paths)} learning paths")

    def get_all_paths(self) -> ResourceHubResponse:
        featured = self._paths[0].path_id if self._paths else ""
        return ResourceHubResponse(paths=self._paths, featured_path_id=featured)

    def get_path(self, path_id: str) -> Optional[LearningPath]:
        for p in self._paths:
            if p.path_id == path_id:
                return p
        return None

    def get_modules_for_sub_path(self, path_id: str, sub_path_id: str) -> List[ResourceModule]:
        """Return ordered modules for a given sub-path."""
        path_data = None
        if not PATHS_FILE.exists():
            return []
        with open(PATHS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for p in raw:
            if p["path_id"] == path_id:
                path_data = p
                break
        if not path_data:
            return []

        sub_paths = path_data.get("sub_paths", [])
        module_ids = []
        for sp in sub_paths:
            if sp["sub_path_id"] == sub_path_id:
                module_ids = sp.get("modules", [])
                break

        raw_modules = path_data.get("modules", {})
        if isinstance(raw_modules, dict):
            return [ResourceModule(**raw_modules[mid]) for mid in module_ids if mid in raw_modules]
        # fallback list
        module_map = {m["module_id"]: m for m in raw_modules}
        return [ResourceModule(**module_map[mid]) for mid in module_ids if mid in module_map]

    def get_module(self, path_id: str, module_id: str) -> Optional[ResourceModule]:
        path = self.get_path(path_id)
        if not path:
            return None
        for m in path.modules:
            if m.module_id == module_id:
                return m
        return None


resource_hub_service = ResourceHubService()
