from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException

from backend.models.marketplace import (
    VendorProfile,
    VendorCreateRequest,
    VendorPresenceRequest,
    CommunityVisitRequest,
    VendorMarketPresence,
    MarketAttendanceResponse,
    ProductSearchResponse,
)
from backend.services.marketplace_store import marketplace_store
from backend.services.product_search_service import product_search_service

router = APIRouter(tags=["Marketplace"])


# ── Vendors (Phase 2) ────────────────────────────────────────

@router.get("/api/vendors", response_model=List[VendorProfile])
def list_vendors(q: Optional[str] = Query(None)):
    return marketplace_store.list_vendors(q=q)


@router.get("/api/vendors/{vendor_id}", response_model=VendorProfile)
def get_vendor(vendor_id: str):
    vendor = marketplace_store.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/api/vendors", response_model=VendorProfile)
def create_vendor(req: VendorCreateRequest):
    return marketplace_store.create_vendor(req)


@router.post("/api/vendors/{vendor_id}/claim", response_model=VendorProfile)
def claim_vendor(vendor_id: str):
    return marketplace_store.claim_vendor(vendor_id)


# ── Market Attendance (Phase 2) ──────────────────────────────

@router.get("/api/markets/{market_id}/attendance", response_model=MarketAttendanceResponse)
def get_market_attendance(
    market_id: str,
    visit_date: Optional[date] = Query(None, description="ISO date YYYY-MM-DD; defaults to today")
):
    target_date = visit_date or date.today()
    return marketplace_store.get_attendance(market_id, target_date)


@router.post("/api/markets/{market_id}/presence", response_model=VendorMarketPresence)
def vendor_report_presence(
    market_id: str,
    req: VendorPresenceRequest,
):
    if not req.vendor_id:
        raise HTTPException(status_code=400, detail="vendor_id is required")
    return marketplace_store.report_vendor_presence(
        market_id=market_id,
        vendor_id=req.vendor_id,
        visit_date=req.visit_date,
        products=req.products_available,
        notes=req.notes,
        booth_hint=req.booth_hint,
        as_vendor=True
    )


@router.post("/api/markets/{market_id}/community-visit", response_model=List[VendorMarketPresence])
def community_log_visit(
    market_id: str,
    req: CommunityVisitRequest,
):
    if len(req.vendor_entries) > 15:
        raise HTTPException(status_code=400, detail="Maximum 15 vendors per community log")
    return marketplace_store.log_community_visit(market_id, req.visit_date, req.vendor_entries)


# ── Product Search (Phase 3) ─────────────────────────────────

@router.get("/api/search/products", response_model=ProductSearchResponse)
def search_products(
    q: str = Query(..., min_length=2, description="What do you want to buy? e.g. goat milk, sourdough"),
    state: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_miles: Optional[float] = Query(25.0),
    when: Optional[str] = Query("any", description="today | this_weekend | any"),
    market_id: Optional[str] = Query(None)
):
    return product_search_service.search(
        q=q,
        state=state,
        lat=lat,
        lon=lon,
        radius_miles=radius_miles,
        when=when,
        market_id=market_id
    )


@router.get("/api/search/product-tags")
def get_product_tags():
    return product_search_service.all_tags()
