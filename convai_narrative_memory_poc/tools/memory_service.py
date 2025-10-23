"""High-level service wrapper around the memory chatbot.

This module exposes a simple request/response interface that keeps track of
memory operations (anchors written, recalls, retells) so UI layers can display
what happened during each turn without needing to understand Kafka plumbing.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .chatbot import MemoryChatbot


@dataclass
class MemoryEvent:
    """Event emitted by the memory system."""

    type: str
    payload: Dict[str, Any]
    timestamp: dt.datetime = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )


@dataclass
class MemoryTurn:
    """Structured representation of a single user/bot exchange."""

    user_text: str
    bot_reply: str
    session_id: str
    anchor_ids: List[str]
    recall: Optional[Dict[str, Any]]
    events: List[MemoryEvent]


class MemoryService:
    """Wrapper that exposes MemoryChatbot interactions as structured data."""

    def __init__(self, persona: Optional[str] = None):
        self._chatbot = MemoryChatbot()
        self._persona = persona

    @property
    def session_id(self) -> str:
        return self._chatbot.session_id

    def reset_session(self, reason: Optional[str] = None) -> MemoryEvent:
        self._chatbot.reset_session(reason=reason)
        return MemoryEvent(
            type="session_reset",
            payload={"reason": reason, "session_id": self.session_id},
        )

    def reset_time(self) -> MemoryEvent:
        self._chatbot.reset_time()
        return MemoryEvent(type="time_reset", payload={})

    def advance_time(
        self, *, days: int = 0, months: int = 0, years: int = 0
    ) -> List[MemoryEvent]:
        self._chatbot.advance_time(days=days, months=months, years=years)
        events = [
            MemoryEvent(
                type="time_advanced",
                payload={"days": days, "months": months, "years": years},
            )
        ]
        events.append(
            self.reset_session(reason="auto-reset after advance_time via service")
        )
        return events

    def set_persona(self, persona: str):
        self._persona = persona

    def get_persona(self) -> Optional[str]:
        return self._persona

    def send_user_message(self, text: str) -> MemoryTurn:
        turn_data = self._chatbot.chat_turn(text, persona=self._persona)
        return self._build_turn(text, turn_data)

    def stream_user_message(
        self, text: str
    ) -> Iterable[tuple[str, Optional[MemoryTurn]]]:
        generator = self._chatbot.chat_turn_stream(text, persona=self._persona)
        turn_data: Optional[Dict[str, Any]] = None
        for chunk in generator:
            if isinstance(chunk, dict):
                turn_data = chunk
            else:
                yield (chunk, None)

        memory_turn = None
        if turn_data:
            memory_turn = self._build_turn(text, turn_data)
        yield ("", memory_turn)

    def _build_turn(self, text: str, turn: Dict[str, Any]) -> MemoryTurn:
        events: List[MemoryEvent] = []
        user_anchor = turn["anchors"].get("user")
        bot_anchor = turn["anchors"].get("bot")

        if user_anchor:
            events.append(
                MemoryEvent(
                    type="anchor_stored",
                    payload={"role": "user", "anchor_id": user_anchor},
                )
            )

        recall_data = turn.get("recall")
        if recall_data:
            events.append(MemoryEvent(type="recall", payload=recall_data))
            beats = recall_data.get("beats") or []
            if beats:
                events.append(MemoryEvent(type="beats", payload={"beats": beats}))
            if recall_data.get("retelling"):
                events.append(
                    MemoryEvent(
                        type="retell",
                        payload={"retelling": recall_data["retelling"]},
                    )
                )

        if bot_anchor:
            events.append(
                MemoryEvent(
                    type="anchor_stored",
                    payload={"role": "bot", "anchor_id": bot_anchor},
                )
            )

        return MemoryTurn(
            user_text=text,
            bot_reply=turn.get("response", ""),
            session_id=self.session_id,
            anchor_ids=[anchor for anchor in [user_anchor, bot_anchor] if anchor],
            recall=recall_data,
            events=events,
        )
