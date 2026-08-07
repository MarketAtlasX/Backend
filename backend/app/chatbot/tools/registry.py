"""Read-only tool registry for the MarketAtlas chatbot.

Tools are currently read-only (market/event/portfolio lookups). They are
described to the LLM in the system prompt so agents can request data by name;
write tools (run simulation, create portfolio) can be added later by
registering a new entry here and routing to the appropriate service.
"""

from typing import Any, Awaitable, Callable, Optional

ToolFn = Callable[..., Awaitable[Any]]


class Tool:
    def __init__(self, name: str, description: str, parameters: str, fn: ToolFn):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.fn = fn

    async def call(self, **kwargs) -> Any:
        try:
            return await self.fn(**kwargs)
        except Exception as exc:
            return {"error": str(exc)}

    def describe(self) -> str:
        return f"{self.name}({self.parameters}) — {self.description}"


async def _tool_live_events() -> dict:
    from sqlalchemy import text

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT title, event_type, severity, source, event_date "
                "FROM events WHERE event_date >= NOW() - INTERVAL '48 hours' "
                "ORDER BY event_date DESC LIMIT 10"
            )
        )
        rows = [dict(r._mapping) for r in result.all()]
    return {"items": rows}


async def _tool_sector_snapshot() -> dict:
    from app.services.sector_data_service import get_sector_snapshot

    return await get_sector_snapshot()


async def _tool_recent_news(limit: int = 5) -> dict:
    from sqlalchemy import text

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT title, source, event_date FROM events ORDER BY event_date DESC LIMIT :n"),
            {"n": min(int(limit), 20)},
        )
        rows = [dict(r._mapping) for r in result.all()]
    return {"items": rows}


def get_tools() -> list[Tool]:
    return [
        Tool(
            "live_events",
            "Recent geopolitical/live events from the last 48 hours",
            "",
            _tool_live_events,
        ),
        Tool(
            "sector_snapshot",
            "Per-sector return and volatility snapshot for the market",
            "",
            _tool_sector_snapshot,
        ),
        Tool(
            "recent_news",
            "Latest news headlines from the events store",
            "limit: int (default 5)",
            _tool_recent_news,
        ),
    ]


def describe_available_tools() -> str:
    return "\n".join(f"- {t.describe()}" for t in get_tools())


async def run_tool(name: str, **kwargs) -> Optional[Any]:
    for tool in get_tools():
        if tool.name == name:
            return await tool.call(**kwargs)
    return None
