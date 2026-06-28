"""Tests for the conditional local-AEO module (modules/local.py). Offline."""

from __future__ import annotations

from damask_engine.models import Status
from damask_engine.modules.local import analyze
from damask_engine.util import make_soup, visible_text


def run(html: str, url: str = "https://acme.test"):
    soup = make_soup(html)
    return {f.id: f for f in analyze(soup, visible_text(soup), url)}


def test_non_local_page_is_silent():
    html = "<body><h1>SaaS platform</h1><p>We sell software to businesses worldwide.</p></body>"
    assert run(html) == {}


def test_tel_link_activates_local_checks():
    # a phone link is a local signal, but with no schema → business_schema warns
    html = '<body><h1>Joe\'s Diner</h1><a href="tel:+15551234567">Call us</a></body>'
    out = run(html)
    assert out  # activated
    assert out["local.business_schema"].status == Status.WARN
    assert out["local.nap"].status == Status.WARN  # phone yes, address no


FULL = """<head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Restaurant","name":"Joe's Diner",
 "telephone":"+1-555-123-4567",
 "address":{"@type":"PostalAddress","streetAddress":"1 Main St","postalCode":"12345"},
 "geo":{"@type":"GeoCoordinates","latitude":"40.1","longitude":"-74.0"},
 "openingHours":"Mo-Fr 09:00-17:00",
 "sameAs":["https://g.page/joes-diner"]}
</script></head><body><h1>Joe's Diner</h1><p>Best diner in town.</p></body>"""


def test_full_localbusiness_schema_passes_everything():
    out = run(FULL)
    assert out["local.business_schema"].status == Status.PASS
    assert "restaurant" in out["local.business_schema"].value["types"]
    assert out["local.nap"].status == Status.PASS
    assert out["local.hours"].status == Status.PASS
    assert out["local.geo"].status == Status.PASS
    assert out["local.gbp"].status == Status.PASS


def test_maps_embed_activates_and_satisfies_geo():
    html = ('<body><h1>Shop</h1>'
            '<iframe src="https://www.google.com/maps/embed?pb=x"></iframe></body>')
    out = run(html)
    assert out["local.geo"].status == Status.PASS  # map embed counts as geo
    assert out["local.business_schema"].status == Status.WARN
