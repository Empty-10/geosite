"""Snapshot test for the JSON report schema (v1).

Pins the report's top-level shape and every finding's keys so an accidental change to the
serialized contract fails loudly. `fetched_at` is the only non-deterministic field and is
checked for presence/type, not value. When the shape changes intentionally, bump
SCHEMA_VERSION and update this test in the same commit.
"""

from __future__ import annotations

from damask_engine import scan_html
from damask_engine.models import SCHEMA_VERSION

HTML = """<!doctype html><html><head>
<title>A clear, useful page title for testing the schema</title>
<meta name="description" content="A description long enough to satisfy the on-page check
without tripping the too-short warning, used purely for the schema snapshot test here.">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head><body><h1>Heading</h1><p>Some body copy for the scan to chew on.</p></body></html>"""

REPORT_KEYS = {"schema_version", "url", "fetched_at", "overall_score", "pillar_scores", "meta", "findings"}
FINDING_KEYS = {"id", "pillar", "title", "status", "severity", "confidence", "value", "evidence", "recommendation"}

ENUM_VALUES = {
    "pillar": {"onpage", "technical", "performance", "local", "geo"},
    "status": {"pass", "warn", "fail", "info"},
    "severity": {"critical", "high", "medium", "low", "info"},
    "confidence": {"verified", "measured", "estimated"},
}


def test_report_schema_snapshot():
    d = scan_html("https://example.com/schema", HTML, online=False).to_dict()

    assert set(d) == REPORT_KEYS
    assert d["schema_version"] == SCHEMA_VERSION == "1"
    assert isinstance(d["fetched_at"], str) and d["fetched_at"]
    assert isinstance(d["overall_score"], int)
    assert isinstance(d["pillar_scores"], dict)
    assert isinstance(d["findings"], list) and d["findings"]

    for f in d["findings"]:
        assert set(f) == FINDING_KEYS, f"finding {f.get('id')} keys drifted: {set(f) ^ FINDING_KEYS}"
        for key, allowed in ENUM_VALUES.items():
            assert f[key] in allowed, f"{f['id']}.{key}={f[key]!r} not in {allowed}"
