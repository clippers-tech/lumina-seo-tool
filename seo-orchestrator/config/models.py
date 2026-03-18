"""
Data models for the SEO Orchestrator.
Strongly-typed dataclasses for pages, actions, and run logs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enums ──────────────────────────────────────────────────────

class PageType(str, Enum):
    MONEY = "money"
    BLOG = "blog"
    SERVICE = "service"
    OTHER = "other"


class ActionType(str, Enum):
    UPDATE_ON_PAGE = "UPDATE_ON_PAGE"
    EXPAND_CONTENT = "EXPAND_CONTENT"
    NEW_ARTICLE = "NEW_ARTICLE"
    TECH_ISSUE = "TECH_ISSUE"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    HUMAN_REVIEW = "human_review"
    SKIPPED = "skipped"


class SiteType(str, Enum):
    NEXTJS = "nextjs"
    VERCEL = "vercel"
    FRAMER = "framer"  # Legacy: luminaclippers.com migrated from Framer to Next.js/Vercel


# ── Page Record ────────────────────────────────────────────────

@dataclass
class PageRecord:
    """Represents a single page with its SEO metrics."""
    url: str
    site: str
    page_type: PageType = PageType.OTHER
    # Rankings
    current_position: Optional[float] = None
    previous_position: Optional[float] = None
    position_delta: Optional[float] = None
    # Traffic (from GSC / GA4 via SearchAtlas)
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    avg_position: float = 0.0
    # SearchAtlas audit metrics
    health_score: Optional[int] = None
    issues_count: int = 0
    issue_types: list[str] = field(default_factory=list)
    # Content
    title: str = ""
    meta_description: str = ""
    h1: str = ""
    word_count: int = 0

    @property
    def opportunity_score(self) -> float:
        """
        Composite opportunity score (higher = better candidate for work).
        Factors: impressions with low CTR, striking distance keywords,
        technical issues, low word count.
        """
        score = 0.0
        # High impressions + low CTR = quick-win title/meta test
        if self.impressions > 50 and self.ctr < 0.03:
            score += 40 + (self.impressions / 100)
        # Striking distance (positions 8-20)
        if self.current_position and 8 <= self.current_position <= 20:
            score += 30 + (20 - self.current_position) * 2
        # Technical issues
        score += self.issues_count * 5
        # Thin content
        if 0 < self.word_count < 500:
            score += 15
        return round(score, 2)


# ── Keyword Record ─────────────────────────────────────────────

@dataclass
class KeywordRecord:
    """Tracked keyword with ranking history."""
    keyword: str
    site: str
    current_position: Optional[float] = None
    previous_position: Optional[float] = None
    position_delta: Optional[float] = None
    search_volume: float = 0.0
    url: str = ""
    serp_features: list[str] = field(default_factory=list)
    location: str = "United States"
    device: str = "desktop"


# ── Action ─────────────────────────────────────────────────────

@dataclass
class Action:
    """A single optimization action to perform."""
    id: str                          # Unique action ID (run_date + index)
    action_type: ActionType
    site: str
    target_url: str
    description: str
    risk_level: RiskLevel = RiskLevel.LOW
    status: ActionStatus = ActionStatus.PROPOSED
    payload: dict = field(default_factory=dict)
    reasoning: str = ""
    keyword: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        d["risk_level"] = self.risk_level.value
        d["status"] = self.status.value
        return d


# ── Run Log ────────────────────────────────────────────────────

@dataclass
class RunLog:
    """Log entry for a single orchestrator run."""
    run_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    sites_processed: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    summary: str = ""
    errors: list[str] = field(default_factory=list)
    data_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "sites_processed": self.sites_processed,
            "actions": [a.to_dict() for a in self.actions],
            "summary": self.summary,
            "errors": self.errors,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
