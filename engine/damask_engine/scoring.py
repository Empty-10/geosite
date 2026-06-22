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


def build_report(url: str, findings: list[Finding], meta: dict | None = None) -> Report:
    report = Report(url=url, findings=findings, meta=meta or {})

    present: dict[Pillar, list[Finding]] = {}
    for f in findings:
        present.setdefault(f.pillar, []).append(f)

    report.pillar_scores = {p.value: score_pillar(fs) for p, fs in present.items()}

    total_weight = sum(PILLAR_WEIGHTS[p] for p in present)
    if total_weight:
        weighted = sum(score_pillar(fs) * PILLAR_WEIGHTS[p] for p, fs in present.items())
        report.overall_score = round(weighted / total_weight)

    return report
