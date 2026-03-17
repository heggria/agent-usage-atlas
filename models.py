"""Data classes and pricing for agent usage tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Model pricing (USD / 1M tokens): {model: (input, cache_read, cache_write, output, reasoning)}
_S = (3, .3, 3.75, 15, 15)
_O = (15, 1.5, 18.75, 75, 75)
_H = (.8, .08, 1, 4, 4)
_OH = (5, .5, 6.25, 25, 25)
_G5 = (2.5, .25, 0, 15, 15)
_G5M = (1.1, .275, 0, 4.4, 4.4)

_P = {
    # OpenAI GPT-5 family
    "gpt-5.4": _G5,
    "gpt-5.3-codex-spark": _G5M,
    "gpt-5.3-codex": _G5,
    "gpt-5.2-codex": _G5,
    "gpt-5.2": _G5,
    "gpt-5.1-codex-max": _G5,
    "gpt-5.1-codex-mini": _G5M,
    "gpt-5.1-codex": _G5,
    "gpt-5.1": _G5,
    "gpt-5-codex-mini": _G5M,
    "gpt-5-codex": _G5,
    "gpt-5": _G5,
    # Anthropic Claude family
    "claude-opus-4-6": _OH, "claude-sonnet-4-6": _S,
    "claude-opus-4-5": _OH, "claude-sonnet-4-5": _S,
    "claude-opus-4-1": _O, "claude-opus-4-0": _O, "claude-opus-4-2": _O,
    "claude-sonnet-4-0": _S, "claude-sonnet-4-2": _S,
    "claude-haiku-4-5": (1, .1, 1.25, 5, 5),
    "claude-haiku-3-5": _H,
    "claude-3-haiku": (.25, .03, .3, 1.25, 1.25),
    "claude-3-5-sonnet": _S, "claude-3-5-haiku": _H, "claude-3-opus": _O,
}


def _gp(model):
    ml = model.lower()
    # Exact prefix match first (longest match wins due to dict order)
    for k, v in _P.items():
        if ml.startswith(k.lower()):
            return v
    # Fallback: substring match
    for k, v in _P.items():
        if k.lower() in ml:
            return v
    return _S


@dataclass
class UsageEvent:
    source: str
    timestamp: datetime
    session_id: str
    model: str
    uncached_input: int = 0
    cache_read: int = 0
    cache_write: int = 0
    output: int = 0
    reasoning: int = 0
    activity_messages: int = 0

    @property
    def total(self):
        return self.uncached_input + self.cache_read + self.cache_write + self.output + self.reasoning

    @property
    def cost(self):
        p = _gp(self.model)
        return (self.uncached_input * p[0] + self.cache_read * p[1] + self.cache_write * p[2]
                + self.output * p[3] + self.reasoning * p[4]) / 1e6

    @property
    def cost_breakdown(self):
        p = _gp(self.model)
        return {
            "input": self.uncached_input * p[0] / 1e6,
            "cache_read": self.cache_read * p[1] / 1e6,
            "cache_write": self.cache_write * p[2] / 1e6,
            "output": self.output * p[3] / 1e6,
            "reasoning": self.reasoning * p[4] / 1e6,
            "cache_read_full": self.cache_read * p[0] / 1e6,
        }


@dataclass
class ToolCall:
    source: str
    timestamp: datetime
    session_id: str
    tool_name: str
    exit_code: int | None = None
    file_path: str | None = None
    command: str | None = None


@dataclass
class SessionMeta:
    source: str
    session_id: str
    cwd: str | None = None
    project: str | None = None
    git_branch: str | None = None


# Formatting helpers
fmt_int = lambda v: f"{v:,}"
fmt_usd = lambda v: f"${v:,.0f}" if v >= 1000 else f"${v:.2f}" if v >= 1 else f"${v:.4f}"
fmt_short = lambda v: (f"{v/1e9:.2f}B" if abs(v) >= 1e9 else f"{v/1e6:.2f}M"
                       if abs(v) >= 1e6 else f"{v/1e3:.1f}K" if abs(v) >= 1e3 else str(v))
