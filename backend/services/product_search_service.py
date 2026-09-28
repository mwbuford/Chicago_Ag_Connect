import json
import math
import re
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.models.marketplace import ProductSearchHit, ProductSearchResponse
from backend.services.data_store import consumer_store
from backend.services.marketplace_store import marketplace_store

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "data" / "product_taxonomy.json"


class ProductSearchService:
    def __init__(self):
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._tags: List[Dict[str, Any]] = data.get("tags", [])
        self._tag_by_id = {t["id"]: t for t in self._tags}

    def get_tag(self, tag_id: str) -> Optional[Dict[str, Any]]:
        return self._tag_by_id.get(tag_id)

    def all_tags(self) -> List[Dict[str, Any]]:
        return self._tags

    def normalize_query(self, q: str) -> tuple[str, List[str]]:
        q_clean = re.sub(r"\s+", " ", q.strip().lower())
        matched = []
        for tag in self._tags:
            terms = [tag["label"].lower()] + [s.lower() for s in tag.get("synonyms", [])]
            for term in terms:
                if term in q_clean or q_clean in term:
                    matched.append(tag["id"])
                    break
        if not matched:
            # partial token match
            tokens = q_clean.split()
            for tag in self._tags:
                label_tokens = tag["label"].lower().split()
                if any(t in label_tokens or t in tag.get("synonyms", []) for t in tokens):
                    matched.append(tag["id"])
        return q_clean, list(dict.fromkeys(matched))

    def search(
        self,
        q: str,
        state: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_miles: Optional[float] = 25.0,
        when: str = "any",
        market_id: Optional[str] = None
    ) -> ProductSearchResponse:
        normalized, matched_tags = self.normalize_query(q)
        if not matched_tags:
            matched_tags = [t["id"] for t in self._tags if normalized in t["label"].lower()]

        hits: List[ProductSearchHit] = []

        # 1. Vendor-confirmed / community presence records (highest trust)
        presence_rows = marketplace_store.list_presences_for_search(
            tag_ids=matched_tags,
            state=state,
            market_id=market_id,
            when=when
        )
        for row in presence_rows:
            p = row["presence"]
            market = row["market"]
            vendor = row["vendor"]
            if lat is not None and lon is not None and radius_miles:
                if self._haversine(lat, lon, market.latitude, market.longitude) > radius_miles:
                    continue

            product_label = self._best_product_label(matched_tags, p.get("products_available", []))
            source = "Vendor confirmed" if p.get("vendor_confirmed") else f"Community reported ({p.get('reported_by')})"

            hits.append(ProductSearchHit(
                hit_type="vendor_presence",
                confidence=p.get("confidence_score", 0.6),
                product_matched=product_label,
                vendor_id=vendor.id,
                vendor_name=vendor.farm_name,
                market_id=market.id,
                market_name=market.name,
                visit_date=date.fromisoformat(p["visit_date"]),
                products=p.get("products_available", []),
                source_label=source,
                latitude=market.latitude,
                longitude=market.longitude,
                city=market.city,
                state_code=market.state_code,
                vendor_confirmed=bool(p.get("vendor_confirmed"))
            ))

        # 2. Direct-sale vendor profiles
        for vendor in marketplace_store.list_direct_vendors_for_search(matched_tags, state=state):
            if lat is not None and lon is not None and radius_miles and vendor.farm_stand_lat and vendor.farm_stand_lon:
                if self._haversine(lat, lon, vendor.farm_stand_lat, vendor.farm_stand_lon) > radius_miles:
                    continue
            hits.append(ProductSearchHit(
                hit_type="vendor_direct",
                confidence=0.9,
                product_matched=self._best_product_label(matched_tags, vendor.product_tags),
                vendor_id=vendor.id,
                vendor_name=vendor.farm_name,
                products=vendor.product_tags,
                source_label="Farm stand / direct sales",
                latitude=vendor.farm_stand_lat,
                longitude=vendor.farm_stand_lon,
                vendor_confirmed=True
            ))

        # 3. USDA fallback (lowest trust)
        if len(hits) < 8:
            from backend.models.spatial import ConsumerMapFilter
            filter_obj = ConsumerMapFilter(state=state or "ALL", search=q)
            usda_locs = consumer_store.query(filter_obj)
            for loc in usda_locs[:15]:
                if lat is not None and lon is not None and radius_miles:
                    if self._haversine(lat, lon, loc.latitude, loc.longitude) > radius_miles:
                        continue
                hits.append(ProductSearchHit(
                    hit_type="usda_location",
                    confidence=0.35,
                    product_matched=q,
                    market_id=loc.id,
                    market_name=loc.name,
                    products=loc.products_offered,
                    source_label="USDA directory (not vendor-verified)",
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    city=loc.city,
                    state_code=loc.state_code,
                    vendor_confirmed=False
                ))

        # Sort by confidence desc, dedupe by vendor+market
        hits.sort(key=lambda h: (-h.confidence, h.vendor_name or h.market_name or ""))
        deduped = self._dedupe_hits(hits)

        return ProductSearchResponse(
            query=q,
            normalized_query=normalized,
            matched_tags=matched_tags,
            results=deduped[:40],
            total=len(deduped)
        )

    def _best_product_label(self, tag_ids: List[str], products: List[str]) -> str:
        for tid in tag_ids:
            tag = self.get_tag(tid)
            if tag:
                return tag["label"]
        return products[0] if products else "Local product"

    def _dedupe_hits(self, hits: List[ProductSearchHit]) -> List[ProductSearchHit]:
        seen = set()
        out = []
        for h in hits:
            key = (h.hit_type, h.vendor_id or "", h.market_id or "", str(h.visit_date))
            if key in seen:
                continue
            seen.add(key)
            out.append(h)
        return out

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        R = 3958.8
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c


product_search_service = ProductSearchService()
