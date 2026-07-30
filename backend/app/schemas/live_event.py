from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums import (
    AssetType,
    ImpactDirection,
    ImpactType,
    LiveEventStatus,
    LiveEventSubType,
    LiveEventType,
    PriceDirection,
    TimeHorizon,
)


def _naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        return v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return v


class LiveEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    event_type: LiveEventType = LiveEventType.GEOPOLITICAL
    sub_type: Optional[LiveEventSubType] = None
    severity: float = Field(default=5.0, ge=0.0, le=10.0)
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: LiveEventStatus = LiveEventStatus.BREAKING
    source: Optional[str] = Field(None, max_length=100)
    source_urls: Optional[list[dict]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    country_code: Optional[str] = Field(None, max_length=2)
    region: Optional[str] = Field(None, max_length=100)
    event_date: Optional[datetime] = None
    extra_meta: Optional[dict] = Field(None, alias="metadata")

    _normalize_date = field_validator("event_date")(_naive_utc)


class LiveEventCreate(LiveEventBase):
    pass


class LiveEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    event_type: Optional[LiveEventType] = None
    sub_type: Optional[LiveEventSubType] = None
    severity: Optional[float] = Field(None, ge=0.0, le=10.0)
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[LiveEventStatus] = None
    source: Optional[str] = Field(None, max_length=100)
    source_urls: Optional[list[dict]] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    country_code: Optional[str] = Field(None, max_length=2)
    region: Optional[str] = Field(None, max_length=100)
    event_date: Optional[datetime] = None
    extra_meta: Optional[dict] = Field(None, alias="metadata")

    _normalize_date = field_validator("event_date")(_naive_utc)


class LiveEventRead(LiveEventBase):
    id: str
    detected_at: Optional[datetime] = None
    first_seen_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventImpactCreate(BaseModel):
    entity_id: Optional[int] = None
    entity_name: str
    entity_type: str
    impact_direction: ImpactDirection = ImpactDirection.NEUTRAL
    impact_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    impact_type: ImpactType = ImpactType.PRICE
    analysis_summary: Optional[str] = None
    reasoning_factors: Optional[dict] = None
    generated_by: str = "ai_service"


class EventImpactRead(EventImpactCreate):
    id: str
    event_id: str
    created_at: datetime
    affected_assets: list["EventAffectedAssetRead"] = []

    model_config = {"from_attributes": True}


class EventAffectedAssetCreate(BaseModel):
    asset_type: AssetType
    ticker: Optional[str] = None
    name: str
    estimated_move: Optional[float] = None
    volatility_impact: Optional[float] = None
    time_horizon: TimeHorizon = TimeHorizon.SHORT_TERM
    current_price: Optional[float] = None
    price_direction: PriceDirection = PriceDirection.MIXED


class EventAffectedAssetRead(EventAffectedAssetCreate):
    id: str
    impact_id: str

    model_config = {"from_attributes": True}


class EventNewsArticleCreate(BaseModel):
    url: str
    title: str
    source: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    content_snippet: Optional[str] = Field(None, max_length=1000)
    sentiment: Optional[float] = None
    relevance_score: Optional[float] = None

    _normalize_date = field_validator("published_at")(_naive_utc)


class EventNewsArticleRead(EventNewsArticleCreate):
    id: str
    event_id: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class EventAlertRead(BaseModel):
    id: str
    user_id: Optional[int] = None
    event_id: Optional[str] = None
    rule_name: Optional[str] = None
    alert_type: str
    title: str
    message: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserEventFilterCreate(BaseModel):
    name: str = Field(..., max_length=100)
    filter_config: dict
    is_default: bool = False


class UserEventFilterRead(UserEventFilterCreate):
    id: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiveEventFullRead(LiveEventRead):
    impacts: list[EventImpactRead] = []
    news_articles: list[EventNewsArticleRead] = []


class LiveEventFeedItem(LiveEventRead):
    impact_count: int = 0
    news_count: int = 0
    top_impact: Optional[EventImpactRead] = None


class LiveEventStats(BaseModel):
    total: int
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_severity_bucket: dict[str, int] = {}
    avg_severity: float = 0.0
    avg_impact_score: Optional[float] = None
    breaking_count: int = 0


class LiveEventTimelineItem(BaseModel):
    bucket: str
    count: int
    avg_severity: float
    top_types: list[str] = []
