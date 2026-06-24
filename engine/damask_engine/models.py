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
# v2: added geo.aeo / geo.faq / geo.trust (+ further coverage-map checks).
# v3: added the top-level `fixes` array (generated remediation artifacts). Snapshot-tested.
# v4: 20-row scorecard parity checks — geo.summary_bullets / geo.intro_quality / geo.chunking,
#     onpage.link_attrs, schema.validation.
# v5: response-header cluster (tech.x_robots_tag / tech.compression / tech.security_headers,
#     live fetch only) + geo.data_density (quotable-data density).
SCHEMA_VERSION = "5"


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
    fixes: list[Any] = field(default_factory=list)  # generated remediation artifacts (Fix)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "url": self.url,
            "fetched_at": self.fetched_at,
            "overall_score": self.overall_score,
            "pillar_scores": self.pillar_scores,
            "meta": self.meta,
            "findings": [f.to_dict() for f in self.findings],
            "fixes": [f.to_dict() for f in self.fixes],
        }


@dataclass
class PageSummary:
    """One page within a site crawl — a compact slice of its full Report.

    The full per-page findings aren't kept (drilling in = re-scanning that URL); a SiteReport
    holds these summaries plus the cross-page `site_findings` a single-page scan can't produce.
    """

    url: str
    status_code: int
    overall_score: int
    pillar_scores: dict[str, int] = field(default_factory=dict)
    title: str = ""
    meta_description: str = ""
    word_count: int = 0
    issues: int = 0  # number of failing/warning findings on the page

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BotActivity:
    """One AI crawler's activity in an analyzed log window."""

    name: str
    operator: str
    category: str  # "training" | "search" | "user" — see crawler_logs.AI_CRAWLERS
    hits: int = 0
    paths: int = 0  # distinct paths requested
    errors: int = 0  # requests that returned 4xx/5xx
    bytes: int = 0
    last_seen: str | None = None
    status_counts: dict[str, int] = field(default_factory=dict)
    top_paths: list[tuple[str, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["top_paths"] = [list(p) for p in self.top_paths]  # JSON has no tuples
        return d


@dataclass
class LogReport:
    """Analysis of an uploaded access log: which AI crawlers visited, what they read, what errored.

    Deterministic and VERIFIED — read straight from the log lines. Separate from the page Report
    (no 0-100 score); it answers "are AI engines actually fetching this site, and successfully?".
    """

    source: str = "uploaded log"
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    bots: list[BotActivity] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)  # line counts, date range, totals

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "scan_type": "logs",
            "source": self.source,
            "fetched_at": self.fetched_at,
            "meta": self.meta,
            "bots": [b.to_dict() for b in self.bots],
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class SiteReport:
    """Aggregate of a multi-page crawl: per-page summaries + site-wide findings + a site score."""

    url: str
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    pages: list[PageSummary] = field(default_factory=list)
    site_findings: list[Finding] = field(default_factory=list)
    overall_score: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "scan_type": "site",
            "url": self.url,
            "fetched_at": self.fetched_at,
            "overall_score": self.overall_score,
            "meta": self.meta,
            "pages": [p.to_dict() for p in self.pages],
            "site_findings": [f.to_dict() for f in self.site_findings],
        }
