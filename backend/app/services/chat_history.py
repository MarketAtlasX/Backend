"""Persistent chat history backed by Postgres (Conversation / ChatMessage).

The in-memory ShortTermMemory still exists for hot path reads, but every
turn is mirrored here so context survives restarts and is scoped per user.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.chat import ChatMessage, Conversation

logger = logging.getLogger(__name__)


def _resolve_user_id(user_id: str | int) -> int:
    """Conversation rows are keyed by int user_id; coerce string ids."""
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return 0


async def get_or_create_conversation(
    conversation_id: str, user_id: str | int, title: str = "Chat"
) -> Optional[Conversation]:
    """Fetch an existing conversation or create one for the user."""
    uid = _resolve_user_id(user_id)
    async with AsyncSessionLocal() as db:
        existing = await db.get(Conversation, conversation_id)
        if existing is not None:
            return existing
        conv = Conversation(id=conversation_id, user_id=uid, title=title)
        db.add(conv)
        try:
            await db.commit()
        except Exception as exc:
            logger.warning("Failed to create conversation %s: %s", conversation_id, exc)
            await db.rollback()
            return None
        return conv


async def persist_turn(
    conversation_id: str,
    user_id: str | int,
    role: str,
    content: str,
    intent: Optional[str] = None,
    agents_used: Optional[list[str]] = None,
    sources: Optional[list[str]] = None,
) -> None:
    """Insert a single chat message into Postgres (best-effort, never raises)."""
    if not content:
        return
    try:
        await get_or_create_conversation(conversation_id, user_id)
    except Exception:
        logger.exception("Could not ensure conversation %s", conversation_id)
    try:
        async with AsyncSessionLocal() as db:
            msg = ChatMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                intent=intent,
                agents_used=json.dumps(agents_used) if agents_used else None,
                sources=json.dumps(sources) if sources else None,
            )
            db.add(msg)
            await db.commit()
    except Exception as exc:
        logger.warning("Failed to persist %s turn for %s: %s", role, conversation_id, exc)


async def get_recent_messages(
    conversation_id: str, limit: int = 20
) -> list[dict[str, str]]:
    """Return the last `limit` messages in chronological order."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            rows = list(result.scalars())
            return [
                {"role": m.role, "content": m.content}
                for m in reversed(rows)
            ]
    except Exception as exc:
        logger.warning("Failed to load history for %s: %s", conversation_id, exc)
        return []


async def format_history_context(conversation_id: str, max_turns: int = 5) -> str:
    """Render the last N turns as USER:/ASSISTANT: plain text for prompts."""
    messages = await get_recent_messages(conversation_id, limit=max_turns)
    if not messages:
        return ""
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


async def list_conversations(user_id: str | int, limit: int = 50) -> list[Conversation]:
    uid = _resolve_user_id(user_id)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == uid)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars())
