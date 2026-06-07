"""
Categorical enumerations for MarketAtlas domain models.

These enums are the single source of truth for all categorical field values.
They are used in:
  - Pydantic schemas (request/response validation)
  - SQLAlchemy model CheckConstraints (DB-level enforcement)

Using StrEnum means the stored and serialised value is the plain string
(e.g. "buy", "high") — no integer codes, no extra mapping needed.
"""

from enum import StrEnum


# ---------------------------------------------------------------------------
# Event enums
# ---------------------------------------------------------------------------

class EventType(StrEnum):
    """Classification of a geopolitical or market event."""

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
    """Impact severity of an event on markets."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventStatus(StrEnum):
    """Lifecycle status of an event record."""

    REPORTED = "reported"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# Entity enums
# ---------------------------------------------------------------------------

class EntityType(StrEnum):
    """Classification of a geopolitical / market entity."""

    COUNTRY = "country"
    COMPANY = "company"
    PERSON = "person"
    REGION = "region"
    INDEX = "index"
    COMMODITY = "commodity"


# ---------------------------------------------------------------------------
# Signal enums
# ---------------------------------------------------------------------------

class SignalType(StrEnum):
    """Actionable direction of a trading signal."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SHORT = "short"


class SignalStatus(StrEnum):
    """Lifecycle status of a trading signal."""

    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
