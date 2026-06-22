"""Offline tests — parse fixed HTML, no network. Run with `pytest`."""

from damask_engine import scan_html
from damask_engine.models import Confidence, Status

GOOD = """
<!doctype html><html><head>
<title>How to brew pour-over coffee at home in 4 steps</title>
<meta name="description" content="A clear, practical guide to brewing better pour-over
coffee at home: the ratio, grind size, water temperature and timing that matter most.">
<link rel="canonical" href="https://example.com/pour-over">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta property="og:title" content="Pour-over coffee guide">
<script type="application/ld+json">{"@type":"Article","headline":"Pour-over guide"}</script>
</head><body>
<h1>How to brew pour-over coffee</h1>
<p>To brew great pour-over coffee, use a 1:16 coffee-to-water ratio, a medium-fine grind,
and water at 96C. Pour in slow circles over about three minutes. This gives a clean, sweet
cup every time.</p>
<h2>What ratio should I use?</h2>
<ul><li>Use 1 gram of coffee to 16 grams of water.</li><li>Weigh, do not guess.</li></ul>
<table><tr><td>Grind</td><td>Medium-fine</td></tr></table>
<p>""" + ("Detailed brewing notes and tips. " * 60) + """</p>
<img src="/cup.jpg" alt="A glass of pour-over coffee">
</body></html>
"""

BAD = "<html><head></head><body><p>buy now</p></body></html>"


def test_good_page_scores_well_and_is_verified():
    r = scan_html("https://example.com/pour-over", GOOD, online=False)
    assert r.overall_score >= 70
    assert all(f.confidence == Confidence.VERIFIED for f in r.findings)
    ids = {f.id: f for f in r.findings}
    assert ids["h1.ok"].status == Status.PASS
    assert ids["schema.jsonld"].status == Status.PASS
    assert ids["geo.structure"].status == Status.PASS
    assert ids["geo.qa_headings"].status == Status.PASS


def test_bad_page_flags_critical_issues():
    r = scan_html("https://example.com/bad", BAD, online=False)
    ids = {f.id: f for f in r.findings}
    assert ids["title.missing"].status == Status.FAIL
    assert ids["h1.missing"].status == Status.FAIL
    assert ids["meta.description.missing"].status == Status.FAIL
    # The on-page pillar should collapse even if other pillars prop the overall up —
    # this is a known scoring nuance (see CLAUDE.md): per-pillar signal matters most.
    assert r.pillar_scores["onpage"] < 60
    assert r.overall_score < r.pillar_scores["technical"]


def test_report_serializes_to_dict():
    r = scan_html("https://example.com", GOOD, online=False)
    d = r.to_dict()
    assert d["url"] == "https://example.com"
    assert "findings" in d and d["findings"]
    assert set(d["pillar_scores"]) <= {"onpage", "technical", "geo"}
