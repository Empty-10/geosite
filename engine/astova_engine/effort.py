"""Deterministic remediation-effort tiers (engine source for the Implementation Programme).

Mirrors the web `effortOf` sets so the programme's effort is computed once, server-side. A tier is a
fixed property of a finding id - no per-page invention. The minutes-per-fix table below is the only
estimate model: a fixed, documented constant per phase bucket (reproducible, not guessed).
"""

from __future__ import annotations

# Quick = a templated / one-line change. Involved = server/infra work. Everything else = Moderate.
EFFORT_QUICK = frozenset({
    "title.length", "title.missing", "meta.description.length", "meta.description.missing",
    "canonical", "onpage.url", "robots.noindex", "robots.indexable", "tech.x_robots_tag",
    "opengraph", "onpage.snippet_directives", "onpage.hreflang", "onpage.lang", "onpage.form_labels",
    "images.alt", "onpage.images.dims", "schema.jsonld", "schema.missing", "schema.validation",
    "tech.llms_txt", "tech.security_headers", "tech.compression", "tech.resource_hints",
    "tech.viewport", "tech.robots.missing", "tech.robots.ai", "tech.sitemap.missing",
    "schema.missing_id", "schema.website_missing_searchaction", "schema.table_extractability",
    "geo.table_extractability", "schema.image_missing_dimensions",
})
EFFORT_INVOLVED = frozenset({
    "tech.https", "tech.tls", "tech.hsts", "tech.redirect", "tech.redirect.chain",
    "tech.mixed_content", "geo.js_rendered", "geo.no_content",
    "perf.score", "perf.lcp", "perf.cls", "perf.tbt", "perf.fcp", "perf.si", "perf.field",
})


def effort_tier(fid: str) -> str:
    if fid in EFFORT_QUICK:
        return "quick"
    if fid in EFFORT_INVOLVED:
        return "involved"
    return "moderate"
