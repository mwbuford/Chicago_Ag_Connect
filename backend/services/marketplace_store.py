import json
import re
import uuid
from datetime import date, datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

from backend.config import MARKETPLACE_DATA_DIR
from backend.models.marketplace import (
    VendorProfile,
    VendorMarketPresence,
    AttendanceVendorRow,
    MarketAttendanceResponse,
    UserAccount,
)
from backend.services.auth_service import auth_service
from backend.services.data_store import consumer_store

VENDORS_FILE = MARKETPLACE_DATA_DIR / "vendors.json"
PRESENCES_FILE = MARKETPLACE_DATA_DIR / "presences.json"
TAXONOMY_FILE = Path(__file__).resolve().parent.parent / "data" / "product_taxonomy.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", name.lower()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


class MarketplaceStore:
    def __init__(self):
        self._vendors: Dict[str, Dict[str, Any]] = {}
        self._presences: List[Dict[str, Any]] = []
        self._taxonomy_tags: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        self._vendors = _load_json(VENDORS_FILE, {})
        self._presences = _load_json(PRESENCES_FILE, [])
        if TAXONOMY_FILE.exists():
            with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
                self._taxonomy_tags = json.load(f).get("tags", [])

    def _persist(self):
        _save_json(VENDORS_FILE, self._vendors)
        _save_json(PRESENCES_FILE, self._presences)

    def list_vendors(self, q: Optional[str] = None) -> List[VendorProfile]:
        vendors = [self._vendor_from_raw(v) for v in self._vendors.values()]
        if q:
            ql = q.lower()
            vendors = [v for v in vendors if ql in v.farm_name.lower()]
        return sorted(vendors, key=lambda v: v.farm_name.lower())

    def get_vendor(self, vendor_id: str) -> Optional[VendorProfile]:
        raw = self._vendors.get(vendor_id)
        return self._vendor_from_raw(raw) if raw else None

    def create_vendor(self, req, user: UserAccount) -> VendorProfile:
        vendor_id = str(uuid.uuid4())[:10]
        raw = {
            "id": vendor_id,
            "farm_name": req.farm_name.strip(),
            "description": req.description,
            "product_tags": req.product_tags,
            "claimed_by_user_id": user.id,
            "sells_direct": req.sells_direct,
            "farm_stand_lat": req.farm_stand_lat,
            "farm_stand_lon": req.farm_stand_lon,
            "website_url": req.website_url,
            "created_at": _utcnow().isoformat()
        }
        self._vendors[vendor_id] = raw
        auth_service.link_vendor(user.id, vendor_id)
        self._persist()
        return self._vendor_from_raw(raw)

    def claim_vendor(self, vendor_id: str, user: UserAccount) -> VendorProfile:
        raw = self._vendors.get(vendor_id)
        if not raw:
            raise HTTPException(status_code=404, detail="Vendor not found")
        if raw.get("claimed_by_user_id") and raw["claimed_by_user_id"] != user.id:
            raise HTTPException(status_code=400, detail="Vendor already claimed by another user")
        raw["claimed_by_user_id"] = user.id
        auth_service.link_vendor(user.id, vendor_id)
        self._persist()
        return self._vendor_from_raw(raw)

    def find_or_create_vendor_stub(self, vendor_name: str, products: List[str]) -> VendorProfile:
        best_id = None
        best_score = 0.0
        for vid, raw in self._vendors.items():
            score = _similarity(vendor_name, raw["farm_name"])
            if score > best_score:
                best_score = score
                best_id = vid

        if best_id and best_score >= 0.82:
            return self._vendor_from_raw(self._vendors[best_id])

        vendor_id = str(uuid.uuid4())[:10]
        raw = {
            "id": vendor_id,
            "farm_name": vendor_name.strip(),
            "description": None,
            "product_tags": products,
            "claimed_by_user_id": None,
            "sells_direct": False,
            "farm_stand_lat": None,
            "farm_stand_lon": None,
            "website_url": None,
            "created_at": _utcnow().isoformat()
        }
        self._vendors[vendor_id] = raw
        self._persist()
        return self._vendor_from_raw(raw)

    def report_vendor_presence(
        self,
        market_id: str,
        vendor_id: str,
        visit_date: date,
        products: List[str],
        user: UserAccount,
        notes: Optional[str] = None,
        booth_hint: Optional[str] = None,
        as_vendor: bool = False
    ) -> VendorMarketPresence:
        market = consumer_store.get_by_id(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        vendor = self.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        if as_vendor:
            if user.vendor_id != vendor_id:
                raise HTTPException(status_code=403, detail="You can only report for your own vendor profile")
            reported_by = "vendor"
            vendor_confirmed = True
            confidence = 1.0
        else:
            reported_by = "community"
            vendor_confirmed = vendor.claimed_by_user_id == user.id
            confidence = 1.0 if vendor_confirmed else 0.55

        presence = {
            "id": str(uuid.uuid4())[:10],
            "market_id": market_id,
            "vendor_id": vendor_id,
            "visit_date": visit_date.isoformat(),
            "products_available": products,
            "reported_by": reported_by,
            "reporter_user_id": user.id,
            "vendor_confirmed": vendor_confirmed,
            "confidence_score": confidence,
            "notes": notes,
            "booth_hint": booth_hint,
            "created_at": _utcnow().isoformat()
        }
        self._presences.append(presence)
        self._merge_vendor_products(vendor_id, products)
        self._persist()
        return self._presence_from_raw(presence)

    def log_community_visit(self, market_id: str, visit_date: date, entries: List[Any], user: UserAccount) -> List[VendorMarketPresence]:
        market = consumer_store.get_by_id(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        created = []
        for entry in entries:
            vendor = self.find_or_create_vendor_stub(entry.vendor_name, entry.products_seen)
            presence = self.report_vendor_presence(
                market_id=market_id,
                vendor_id=vendor.id,
                visit_date=visit_date,
                products=entry.products_seen,
                user=user,
                booth_hint=entry.booth_hint,
                as_vendor=False
            )
            created.append(presence)
        return created

    def get_attendance(self, market_id: str, visit_date: date) -> MarketAttendanceResponse:
        market = consumer_store.get_by_id(market_id)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        date_str = visit_date.isoformat()
        rows_by_vendor: Dict[str, Dict[str, Any]] = {}

        for p in self._presences:
            if p["market_id"] != market_id or p["visit_date"] != date_str:
                continue
            vid = p["vendor_id"]
            vendor = self.get_vendor(vid)
            if not vendor:
                continue

            if vid not in rows_by_vendor:
                rows_by_vendor[vid] = {
                    "vendor_id": vid,
                    "farm_name": vendor.farm_name,
                    "products": set(p.get("products_available", [])),
                    "vendor_confirmed": p.get("vendor_confirmed", False),
                    "community_count": 0,
                    "vendor_reports": 0,
                    "notes": p.get("notes"),
                    "booth_hint": p.get("booth_hint"),
                    "confidence": p.get("confidence_score", 0.5)
                }

            row = rows_by_vendor[vid]
            row["products"].update(p.get("products_available", []))
            if p.get("reported_by") == "vendor":
                row["vendor_reports"] += 1
                row["vendor_confirmed"] = True
            else:
                row["community_count"] += 1
            if p.get("notes"):
                row["notes"] = p["notes"]
            if p.get("booth_hint"):
                row["booth_hint"] = p["booth_hint"]

        merged_rows: List[AttendanceVendorRow] = []
        for row in rows_by_vendor.values():
            if row["vendor_confirmed"]:
                confidence = 1.0
                reported_by = "vendor" if row["vendor_reports"] > 0 else "merged"
            elif row["community_count"] >= 3:
                confidence = 0.85
                reported_by = "community"
            else:
                confidence = min(0.75, 0.55 + row["community_count"] * 0.1)
                reported_by = "community"

            merged_rows.append(AttendanceVendorRow(
                vendor_id=row["vendor_id"],
                farm_name=row["farm_name"],
                products_available=sorted(row["products"]),
                reported_by=reported_by,
                vendor_confirmed=row["vendor_confirmed"],
                confidence_score=round(confidence, 2),
                community_report_count=row["community_count"],
                notes=row.get("notes"),
                booth_hint=row.get("booth_hint")
            ))

        merged_rows.sort(key=lambda r: (-r.confidence_score, r.farm_name.lower()))

        return MarketAttendanceResponse(
            market_id=market_id,
            market_name=market.name,
            visit_date=visit_date,
            vendors=merged_rows,
            total_vendors=len(merged_rows)
        )

    def list_presences_for_search(
        self,
        tag_ids: List[str],
        state: Optional[str] = None,
        market_id: Optional[str] = None,
        when: str = "any"
    ) -> List[Dict[str, Any]]:
        results = []
        for p in self._presences:
            if market_id and p["market_id"] != market_id:
                continue

            market = consumer_store.get_by_id(p["market_id"])
            if not market:
                continue
            if state and market.state_code.upper() != state.upper():
                continue

            visit = date.fromisoformat(p["visit_date"])
            if not self._date_matches_when(visit, when):
                continue

            products = [x.lower() for x in p.get("products_available", [])]
            vendor = self.get_vendor(p["vendor_id"])
            if not vendor:
                continue

            vendor_tags = [t.lower() for t in vendor.product_tags]
            combined = products + vendor_tags

            if not self._matches_any_tag(tag_ids, combined, products):
                continue

            results.append({
                "presence": p,
                "market": market,
                "vendor": vendor
            })
        return results

    def list_direct_vendors_for_search(self, tag_ids: List[str], state: Optional[str] = None) -> List[VendorProfile]:
        hits = []
        for raw in self._vendors.values():
            vendor = self._vendor_from_raw(raw)
            if not vendor.sells_direct:
                continue
            tags = [t.lower() for t in vendor.product_tags]
            if self._matches_any_tag(tag_ids, tags, tags):
                hits.append(vendor)
        return hits

    def _matches_any_tag(self, tag_ids: List[str], haystack: List[str], raw_products: List[str]) -> bool:
        tag_by_id = {t["id"]: t for t in self._taxonomy_tags}
        for tag_id in tag_ids:
            tag = tag_by_id.get(tag_id)
            if not tag:
                continue
            terms = [tag["label"].lower()] + [s.lower() for s in tag.get("synonyms", [])]
            for term in terms:
                if any(term in h for h in haystack):
                    return True
                if any(term in p for p in raw_products):
                    return True
        return False

    def _date_matches_when(self, visit: date, when: str) -> bool:
        today = date.today()
        if when == "any":
            return visit >= today - timedelta(days=30)
        if when == "today":
            return visit == today
        if when == "this_weekend":
            # Saturday or Sunday of current week
            weekday = today.weekday()
            days_to_sat = (5 - weekday) % 7
            sat = today + timedelta(days=days_to_sat)
            sun = sat + timedelta(days=1)
            return visit in {sat, sun, today}
        return True

    def _merge_vendor_products(self, vendor_id: str, products: List[str]):
        raw = self._vendors.get(vendor_id)
        if not raw:
            return
        existing = set(raw.get("product_tags", []))
        for p in products:
            if p and p not in existing:
                raw.setdefault("product_tags", []).append(p)
        self._persist()

    def _vendor_from_raw(self, raw: Dict[str, Any]) -> VendorProfile:
        return VendorProfile(
            id=raw["id"],
            farm_name=raw["farm_name"],
            description=raw.get("description"),
            product_tags=raw.get("product_tags", []),
            claimed_by_user_id=raw.get("claimed_by_user_id"),
            sells_direct=raw.get("sells_direct", False),
            farm_stand_lat=raw.get("farm_stand_lat"),
            farm_stand_lon=raw.get("farm_stand_lon"),
            website_url=raw.get("website_url"),
            created_at=datetime.fromisoformat(raw["created_at"])
        )

    def _presence_from_raw(self, raw: Dict[str, Any]) -> VendorMarketPresence:
        return VendorMarketPresence(
            id=raw["id"],
            market_id=raw["market_id"],
            vendor_id=raw["vendor_id"],
            visit_date=date.fromisoformat(raw["visit_date"]),
            products_available=raw.get("products_available", []),
            reported_by=raw["reported_by"],
            reporter_user_id=raw["reporter_user_id"],
            vendor_confirmed=raw.get("vendor_confirmed", False),
            confidence_score=raw.get("confidence_score", 0.5),
            notes=raw.get("notes"),
            booth_hint=raw.get("booth_hint"),
            created_at=datetime.fromisoformat(raw["created_at"])
        )


marketplace_store = MarketplaceStore()
