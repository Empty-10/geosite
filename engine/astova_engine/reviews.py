"""Shared Expert Review contract - the standard every Astova review renders from.

This is a design contract enforced by reuse, not a base class. Each review (Answerability now;
Schema / Crawlability / Trust / Metadata / Internal-Linking later) builds the SAME shape via these
helpers and attaches it additively under report.scorecard["reviews"][<key>]. Pure + deterministic:
no network, no LLM. "Confidence" is Astova's confidence in its own review, NOT page quality.
"""

from __future__ import annotations

from . import knowledge

_ACTIONABLE = ("fail", "warn")
_SEV = ("critical", "high", "medium", "low", "info")

# Findings whose remediation is editorial (draft from real content) - AI-assisted, never auto-applied.
# Mirrors the web GENERATIVE_FINDINGS set; kept here so reviews can bucket engine-side.
AI_ASSISTED_FINDINGS = {
    "geo.aeo", "geo.frontload", "geo.definitive", "geo.thin_content", "geo.intro_quality",
    "geo.answer_self_contained", "geo.definition_present", "geo.question_coverage",
}


def status_map(findings: list[dict]) -> dict[str, str]:
    """finding id -> status, for the latest occurrence of each id."""
    return {f["id"]: f["status"] for f in findings}


def review_confidence(meta: dict, findings: list[dict], extra_reasons: list[str] | None = None) -> dict:
    """Astova's deterministic confidence in its own review of this page: high / medium / low + reasons.

    Reviews may pass review-specific `extra_reasons` (each lowers toward medium). NOT page quality -
    it reflects how much of the real page Astova could actually see.
    """
    sm = status_map(findings)
    rendered = bool(meta.get("rendered") or meta.get("render_source"))
    reasons: list[str] = []
    low = False
    medium = False

    if meta.get("challenge", {}).get("detected"):
        reasons.append("a bot-protection challenge was served, not the real page")
        low = True
    if meta.get("error"):
        reasons.append("the page could not be fetched cleanly")
        low = True
    if sm.get("geo.no_content") == "fail" or (isinstance(meta.get("word_count"), int) and meta["word_count"] < 10):
        reasons.append("almost no readable content to assess")
        low = True
    if sm.get("geo.js_rendered") == "fail" and not rendered:
        reasons.append("most content is JavaScript-rendered and was not captured")
        low = True

    if sm.get("geo.js_rendered") in ("warn", "fail"):
        reasons.append("some content is JavaScript-rendered")
        medium = True
    wc = meta.get("word_count")
    if isinstance(wc, int) and 10 <= wc < 150:
        reasons.append("limited readable content")
        medium = True
    if sm.get("canonical") in ("warn", "fail"):
        reasons.append("no canonical context declared")
        medium = True

    for r in extra_reasons or []:
        reasons.append(r)
        medium = True

    if low:
        level = "low"
    elif medium:
        level = "medium"
    else:
        level = "high"
        reasons = ["full HTML analysed"]
    return {"level": level, "reasons": reasons}


def finding_class(fid: str, fix_ids: set[str]) -> str:
    """The remediation class of a single finding: 'deterministic' (a ready Astova fix, or the card
    says deterministic), 'ai_assisted' (editorial, draftable from real content), or 'manual'."""
    card = knowledge.explain(fid) or {}
    if fid in fix_ids or card.get("can_astova_generate") == "deterministic":
        return "deterministic"
    if fid in AI_ASSISTED_FINDINGS or card.get("can_astova_generate") == "ai_assisted":
        return "ai_assisted"
    return "manual"


def classify_findings(finding_ids: list[str], by_id: dict[str, dict], fix_ids: set[str]) -> dict:
    """Issue counts + the standard remediation buckets for a review's findings."""
    issues = [fid for fid in finding_ids if by_id.get(fid, {}).get("status") in _ACTIONABLE]
    critical_high = sum(1 for fid in issues if by_id[fid].get("severity") in ("critical", "high"))
    buckets = {"deterministic": 0, "ai_assisted": 0, "manual": 0}
    for fid in issues:
        buckets[finding_class(fid, fix_ids)] += 1
    return {
        "issues": len(issues),
        "critical_high": critical_high,
        "deterministic_fixes": buckets["deterministic"],
        "ai_assisted": buckets["ai_assisted"],
        "manual": buckets["manual"],
    }


def build_review(*, key: str, name: str, verdict: str, confidence: dict, summary: list[str],
                 sections: list[dict], counts: dict, related_findings: list[str],
                 likely_ai_quote: str | None = None) -> dict:
    """Assemble the standard Expert Review contract object."""
    return {
        "review": name,
        "key": key,
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "likely_ai_quote": likely_ai_quote,
        "sections": sections,
        "counts": counts,
        "related_findings": related_findings,
    }


def section_status(finding_ids: list[str], by_id: dict[str, dict]) -> str:
    """Roll a section's findings up to pass / attention / fail (only findings actually present count)."""
    statuses = [by_id[f]["status"] for f in finding_ids if f in by_id]
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "attention"
    return "pass"
