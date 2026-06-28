"""Turn a flat list of findings into pillar scores and an overall score.

Each pillar starts at 100 and loses points per failing/warning check (severity-weighted,
capped at 0). The overall score is a weighted average of the pillars that were actually
run, with weights renormalized so partial scans still produce a sensible 0–100.
"""

from __future__ import annotations

from .models import Finding, Pillar, Report

# Target weights from the architecture. Renormalized over whichever pillars ran.
PILLAR_WEIGHTS: dict[Pillar, int] = {
    Pillar.TECHNICAL: 25,
    Pillar.ONPAGE: 25,
    Pillar.PERFORMANCE: 20,
    Pillar.GEO: 20,
    Pillar.LOCAL: 10,
}


def score_pillar(findings: list[Finding]) -> int:
    score = 100 - sum(f.penalty for f in findings)
    return max(0, min(100, score))


def build_report(url: str, findings: list[Finding], meta: dict | None = None,
                 pillar_overrides: dict[Pillar, int] | None = None) -> Report:
    """Score a list of findings into a Report.

    `pillar_overrides` lets a pillar carry an authoritative score from its source instead of
    the penalty model — used for Performance, whose score IS Google's Lighthouse 0–100 rather
    than something we re-derive from findings.
    """
    report = Report(url=url, findings=findings, meta=meta or {})
    overrides = pillar_overrides or {}

    present: dict[Pillar, list[Finding]] = {}
    for f in findings:
        present.setdefault(f.pillar, []).append(f)

    def pillar_value(p: Pillar, fs: list[Finding]) -> int:
        return overrides[p] if p in overrides else score_pillar(fs)

    report.pillar_scores = {p.value: pillar_value(p, fs) for p, fs in present.items()}

    total_weight = sum(PILLAR_WEIGHTS[p] for p in present)
    if total_weight:
        weighted = sum(report.pillar_scores[p.value] * PILLAR_WEIGHTS[p] for p in present)
        report.overall_score = round(weighted / total_weight)

    return report
