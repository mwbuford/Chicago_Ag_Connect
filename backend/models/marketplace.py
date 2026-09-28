from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    CONSUMER = "consumer"
    VENDOR = "vendor"
    MODERATOR = "moderator"


class UserAccount(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole = UserRole.CONSUMER
    vendor_id: Optional[str] = None
    created_at: datetime


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    display_name: str = Field(..., min_length=2, max_length=80)
    role: UserRole = UserRole.CONSUMER


class UserLoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserAccount


class VendorProfile(BaseModel):
    id: str
    farm_name: str
    description: Optional[str] = None
    product_tags: List[str] = Field(default_factory=list)
    claimed_by_user_id: Optional[str] = None
    sells_direct: bool = False
    farm_stand_lat: Optional[float] = None
    farm_stand_lon: Optional[float] = None
    website_url: Optional[str] = None
    created_at: datetime


class VendorCreateRequest(BaseModel):
    farm_name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    product_tags: List[str] = Field(default_factory=list)
    sells_direct: bool = False
    farm_stand_lat: Optional[float] = None
    farm_stand_lon: Optional[float] = None
    website_url: Optional[str] = None


class VendorMarketPresence(BaseModel):
    id: str
    market_id: str
    vendor_id: str
    visit_date: date
    products_available: List[str] = Field(default_factory=list)
    reported_by: Literal["vendor", "community"]
    reporter_user_id: str
    vendor_confirmed: bool = False
    confidence_score: float = 0.5
    notes: Optional[str] = None
    booth_hint: Optional[str] = None
    created_at: datetime


class VendorPresenceRequest(BaseModel):
    vendor_id: Optional[str] = None
    visit_date: date
    products_available: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    booth_hint: Optional[str] = None


class CommunityVendorEntryRequest(BaseModel):
    vendor_name: str = Field(..., min_length=2, max_length=120)
    products_seen: List[str] = Field(default_factory=list)
    booth_hint: Optional[str] = None


class CommunityVisitRequest(BaseModel):
    visit_date: date
    vendor_entries: List[CommunityVendorEntryRequest] = Field(..., min_length=1)


class AttendanceVendorRow(BaseModel):
    vendor_id: str
    farm_name: str
    products_available: List[str]
    reported_by: Literal["vendor", "community", "merged"]
    vendor_confirmed: bool
    confidence_score: float
    community_report_count: int = 0
    notes: Optional[str] = None
    booth_hint: Optional[str] = None


class MarketAttendanceResponse(BaseModel):
    market_id: str
    market_name: str
    visit_date: date
    vendors: List[AttendanceVendorRow]
    total_vendors: int


class ProductSearchRequest(BaseModel):
    q: str = Field(..., min_length=2)
    state: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_miles: Optional[float] = 25.0
    when: Optional[Literal["today", "this_weekend", "any"]] = "any"
    market_id: Optional[str] = None


class ProductSearchHit(BaseModel):
    hit_type: Literal["vendor_presence", "vendor_direct", "usda_location"]
    confidence: float
    product_matched: str
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    market_id: Optional[str] = None
    market_name: Optional[str] = None
    visit_date: Optional[date] = None
    products: List[str] = Field(default_factory=list)
    source_label: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state_code: Optional[str] = None
    vendor_confirmed: bool = False


class ProductSearchResponse(BaseModel):
    query: str
    normalized_query: str
    matched_tags: List[str]
    results: List[ProductSearchHit]
    total: int
