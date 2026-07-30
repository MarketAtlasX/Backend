from enum import StrEnum


class EventType(StrEnum):
    SANCTION = "sanction"
    ELECTION = "election"
    TRADE_POLICY = "trade_policy"
    MILITARY_CONFLICT = "military_conflict"
    DIPLOMATIC = "diplomatic"
    ECONOMIC_DATA = "economic_data"
    REGULATORY = "regulatory"
    NATURAL_DISASTER = "natural_disaster"
    OTHER = "other"


class EventSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(StrEnum):
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"


class EntityType(StrEnum):
    COUNTRY = "country"
    COMPANY = "company"
    PERSON = "person"
    REGION = "region"
    INDEX = "index"
    COMMODITY = "commodity"


class SignalType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SHORT = "short"


class SignalStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"


class LiveEventType(StrEnum):
    GEOPOLITICAL = "geopolitical"
    ECONOMIC = "economic"
    CORPORATE = "corporate"
    MARKET_MOVING = "market_moving"
    REGULATORY = "regulatory"
    NATURAL_DISASTER = "natural_disaster"
    OTHER = "other"


class LiveEventSubType(StrEnum):
    SANCTION = "sanction"
    RATE_HIKE = "rate_hike"
    MERGER = "merger"
    EARNINGS = "earnings"
    CONFLICT = "conflict"
    ELECTION = "election"
    TRADE_AGREEMENT = "trade_agreement"
    SUPPLY_DISRUPTION = "supply_disruption"
    DIPLOMATIC_TENSION = "diplomatic_tension"
    ECONOMIC_DATA = "economic_data"
    REGULATORY_CHANGE = "regulatory_change"
    NATURAL_DISASTER = "natural_disaster"
    CORPORATE_EVENT = "corporate_event"
    MARKET_MOVE = "market_move"
    OTHER = "other"


class LiveEventStatus(StrEnum):
    BREAKING = "breaking"
    CONFIRMED = "confirmed"
    DEVELOPING = "developing"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class ImpactDirection(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ImpactType(StrEnum):
    PRICE = "price"
    SUPPLY_CHAIN = "supply_chain"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"
    DEMAND = "demand"
    REPUTATIONAL = "reputational"


class AssetType(StrEnum):
    STOCK = "stock"
    COMMODITY = "commodity"
    INDEX = "index"
    BOND = "bond"
    CURRENCY = "currency"
    ETF = "etf"


class TimeHorizon(StrEnum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class PriceDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    MIXED = "mixed"


class AlertType(StrEnum):
    PUSH = "push"
    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class AlertTriggerType(StrEnum):
    SEVERITY_THRESHOLD = "severity_threshold"
    EVENT_TYPE = "event_type"
    ENTITY = "entity"
    SECTOR = "sector"
    COUNTRY = "country"
    KEYWORD = "keyword"
