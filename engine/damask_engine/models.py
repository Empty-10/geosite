"""Core data model for the scan engine.

The confidence label is the heart of the product: it makes the deterministic-vs-
probabilistic split explicit and enforced, so an estimate can never masquerade as a fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Bump when the report's check coverage or shape changes in a way consumers should notice.
# v2: added geo.aeo / geo.faq / geo.trust (+ further coverage-map checks). Snapshot-tested.
SCHEMA_VERSION = "2"


class Confidence(str, Enum):
    """How much to trust a finding. See CLAUDE.md → accuracy principle."""

    VERIFIED = "verified"  # read straight from the page/API; reproducible
    MEASURED = "measured"  # sampled from AI engines on a date; has a confidence band
    ESTIMATED = "estimated"  # modelled/inferred; directional only


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"


class Pillar(str, Enum):
    ONPAGE = "onpage"
    TECHNICAL = "technical"
    PERFORMANCE = "performance"
    LOCAL = "local"
    GEO = "geo"  # GEO readiness (deterministic). Citation sampling is separate + MEASURED.


# Severity → score penalty (points off a 100 pillar score when a check fails/warns).
_PENALTY = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFO: 0,
}


@dataclass
class Finding:
    """A single check result. Modules return lists of these and nothing else."""

    id: str
    pillar: Pillar
    title: str
    status: Status
    severity: Severity = Severity.INFO
    confidence: Confidence = Confidence.VERIFIED
    value: Any = None  # the measured value (e.g. title length, word count)
    evidence: str | None = None  # the exact source line / snippet behind the finding
    recommendation: str | None = None  # plain-English fix

    @property
    def penalty(self) -> int:
        """Points deducted from the pillar score. Only failing/warning checks cost."""
        if self.status == Status.FAIL:
            return _PENALTY[self.severity]
        if self.status == Status.WARN:
            return _PENALTY[self.severity] // 2
        return 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pillar"] = self.pillar.value
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        d["confidence"] = self.confidence.value
        return d


@dataclass
class Report:
    url: str
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings: list[Finding] = field(default_factory=list)
    pillar_scores: dict[str, int] = field(default_factory=dict)
    overall_score: int = 0
    meta: dict[str, Any] = field(default_factory=dict)  # status code, fetch notes, etc.

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "url": self.url,
            "fetched_at": self.fetched_at,
            "overall_score": self.overall_score,
            "pillar_scores": self.pillar_scores,
            "meta": self.meta,
            "findings": [f.to_dict() for f in self.findings],
        }
