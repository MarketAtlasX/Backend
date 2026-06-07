from pydantic import BaseModel, Field

from app.schemas.event import EventRead
from app.schemas.signal import SignalRead


class AnalyzeEventRequest(BaseModel):
    entity_ids: list[int] | None = Field(
        None,
        description="Optional list of entity IDs to analyze. If omitted, analyzes all entities linked to the event.",
    )


class AnalyzeEventResponse(BaseModel):
    event: EventRead = Field(description="The analyzed event")
    signals: list[SignalRead] = Field(
        default_factory=list, description="Generated trading signals"
    )
