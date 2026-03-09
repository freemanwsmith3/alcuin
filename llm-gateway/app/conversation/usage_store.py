from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Pricing per 1M tokens (USD). Add models here as needed.
PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
    "claude-opus-4-6":           {"input": 15.00, "output": 75.00},
    "gpt-4o":                    {"input": 5.00, "output": 15.00},
    "gpt-4o-mini":               {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo":             {"input": 0.50, "output": 1.50},
}


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model)
    if not prices:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


@dataclass
class UsageRecord:
    session_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionTotal:
    session_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    request_count: int = 0


class UsageStore:
    """In-memory store for per-request token usage and cost tracking."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._totals: dict[str, SessionTotal] = defaultdict(
            lambda: SessionTotal(session_id="")
        )

    def record(
        self,
        session_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        cost = _cost_usd(model, input_tokens, output_tokens)
        self._records.append(
            UsageRecord(
                session_id=session_id,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
        )
        t = self._totals[session_id]
        t.session_id = session_id
        t.input_tokens += input_tokens
        t.output_tokens += output_tokens
        t.cost_usd += cost
        t.request_count += 1

    def get_session(self, session_id: str) -> SessionTotal | None:
        return self._totals.get(session_id)

    def get_all_sessions(self) -> list[SessionTotal]:
        return list(self._totals.values())

    def grand_total(self) -> dict:
        totals = self.get_all_sessions()
        return {
            "sessions": len(totals),
            "requests": sum(t.request_count for t in totals),
            "input_tokens": sum(t.input_tokens for t in totals),
            "output_tokens": sum(t.output_tokens for t in totals),
            "cost_usd": round(sum(t.cost_usd for t in totals), 6),
        }
