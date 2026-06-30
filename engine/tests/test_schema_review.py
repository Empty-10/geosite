"""Tests for the Expert Schema Review module (schema_review.analyze)."""

from __future__ import annotations

from astova_engine import knowledge, scan_html
from astova_engine.fixes import generate_fix
from astova_engine.modules import schema_review
from astova_engine.util import make_soup

URL = "https://acme.com/page"


def _ids(html, url=URL):
    return {f.id for f in schema_review.analyze(make_soup(html), url)}


def _ld(body):
    return f'<script type="application/ld+json">{body}</script>'


CLEAN = _ld('{"@context":"https://schema.org","@graph":['
            '{"@type":"Organization","@id":"https://acme.com/#org","name":"Acme","url":"https://acme.com",'
            '"logo":{"@type":"ImageObject","url":"https://acme.com/l.png","width":200,"height":60},'
            '"sameAs":["https://twitter.com/acme","https://www.linkedin.com/company/acme"]},'
            '{"@type":"WebPage","@id":"https://acme.com/page#wp","url":"https://acme.com/page"}]}')


def test_clean_schema_passes():
    assert _ids(CLEAN) == set()


def test_no_schema_returns_nothing():
    assert _ids("<html><body><p>no schema here</p></body></html>") == set()


# --------------------------------------------------------------------------- duplication / conflicts

def test_duplicate_organization():
    html = _ld('[{"@type":"Organization","name":"Acme","url":"https://acme.com"},'
               '{"@type":"Organization","name":"Acme","url":"https://acme.com"}]')
    assert "schema.duplicate_organization" in _ids(html)


def test_conflicting_organization_name_and_url():
    html = _ld('[{"@type":"Organization","name":"Acme","url":"https://acme.com"},'
               '{"@type":"Organization","name":"Acme Inc","url":"https://acme.io"}]')
    ids = _ids(html)
    assert "schema.conflicting_organization_name" in ids
    assert "schema.conflicting_organization_url" in ids


def test_duplicate_website_and_localbusiness():
    html = _ld('[{"@type":"WebSite","url":"https://acme.com"},{"@type":"WebSite","url":"https://acme.com"},'
               '{"@type":"LocalBusiness","name":"A"},{"@type":"Restaurant","name":"B"}]')
    ids = _ids(html)
    assert "schema.duplicate_website" in ids
    assert "schema.duplicate_localbusiness" in ids


def test_duplicate_id_conflict():
    html = _ld('[{"@type":"Organization","@id":"https://acme.com/#x","name":"Acme"},'
               '{"@type":"WebSite","@id":"https://acme.com/#x","url":"https://acme.com"}]')
    assert "schema.duplicate_id_conflict" in _ids(html)


# --------------------------------------------------------------------------- @id / graph wiring

def test_missing_id_in_graph():
    html = _ld('[{"@type":"Organization","name":"Acme","url":"https://acme.com"},'
               '{"@type":"WebPage","url":"https://acme.com/page"}]')
    assert "schema.missing_id" in _ids(html)


def test_breadcrumb_disconnected():
    html = _ld('[{"@type":"WebPage","@id":"https://acme.com/page#wp","url":"https://acme.com/page"},'
               '{"@type":"BreadcrumbList","@id":"https://acme.com/page#bc",'
               '"itemListElement":[{"@type":"ListItem","position":1,"name":"Home"}]}]')
    assert "schema.breadcrumb_disconnected" in _ids(html)


def test_breadcrumb_connected_ok():
    html = _ld('[{"@type":"WebPage","url":"https://acme.com/page","breadcrumb":{"@id":"https://acme.com/page#bc"}},'
               '{"@type":"BreadcrumbList","@id":"https://acme.com/page#bc",'
               '"itemListElement":[{"@type":"ListItem","position":1,"name":"Home"}]}]')
    assert "schema.breadcrumb_disconnected" not in _ids(html)


# --------------------------------------------------------------------------- sameAs

def test_invalid_sameas():
    html = _ld('{"@type":"Organization","name":"Acme","sameAs":["not-a-url","https://x.com/acme"]}')
    assert "schema.invalid_sameas" in _ids(html)


def test_weak_sameas_empty():
    html = _ld('{"@type":"Organization","name":"Acme","sameAs":[]}')
    assert "schema.weak_sameas" in _ids(html)


# --------------------------------------------------------------------------- article relationships

def test_article_missing_publisher_and_author():
    html = _ld('{"@type":"Article","headline":"Hello world"}')
    ids = _ids(html)
    assert "schema.article_missing_publisher" in ids
    assert "schema.article_missing_author" in ids


def test_article_with_relationships_ok():
    html = _ld('{"@type":"Article","headline":"Hi","author":{"@type":"Person","name":"Jo"},'
               '"publisher":{"@id":"https://acme.com/#org"}}')
    ids = _ids(html)
    assert "schema.article_missing_publisher" not in ids
    assert "schema.article_missing_author" not in ids


# --------------------------------------------------------------------------- url / type hygiene

def test_canonical_mismatch():
    html = ('<link rel="canonical" href="https://acme.com/post">'
            + _ld('{"@type":"WebPage","url":"https://acme.com/different"}'))
    assert "schema.canonical_mismatch" in _ids(html, "https://acme.com/post")


def test_insecure_url_on_https_page():
    html = _ld('{"@type":"Organization","name":"Acme","url":"http://acme.com","logo":"http://acme.com/l.png"}')
    assert "schema.insecure_url" in _ids(html, "https://acme.com/page")


def test_insecure_url_not_flagged_on_http_page():
    html = _ld('{"@type":"Organization","name":"Acme","url":"http://acme.com"}')
    assert "schema.insecure_url" not in _ids(html, "http://acme.com/page")


def test_image_missing_dimensions():
    html = _ld('{"@type":"Organization","name":"Acme","logo":{"@type":"ImageObject","url":"https://acme.com/l.png"}}')
    assert "schema.image_missing_dimensions" in _ids(html)


def test_generic_type_thing():
    html = _ld('{"@type":"Thing","name":"Acme"}')
    assert "schema.generic_type" in _ids(html)


def test_searchaction_only_when_search_box_present():
    site = _ld('{"@type":"WebSite","url":"https://acme.com"}')
    assert "schema.website_missing_searchaction" not in _ids(site)  # no search box
    with_search = site + '<input type="search" name="q">'
    assert "schema.website_missing_searchaction" in _ids(with_search)


# --------------------------------------------------------------------------- regression guards

def test_existing_schema_missing_unchanged():
    # onpage still emits schema.missing for a page with no JSON-LD; schema_review adds nothing.
    d = scan_html("https://acme.com/x", "<html><head></head><body><h1>Hi</h1></body></html>",
                  online=False).to_dict()
    ids = {f["id"] for f in d["findings"]}
    assert "schema.missing" in ids
    assert not any(i.startswith("schema.") and i != "schema.missing" for i in ids)


def test_existing_schema_fix_unchanged():
    fx = generate_fix("schema.missing", {"url": "https://acme.com/p"})
    assert fx["supported"] and "Organization" in fx["generated_content"]


def test_searchaction_deterministic_fix():
    fx = generate_fix("schema.website_missing_searchaction", {"url": "https://acme.com/page"})
    assert fx["supported"] and "SearchAction" in fx["generated_content"]
    assert "search_term_string" in fx["generated_content"]


def test_every_new_finding_has_a_card():
    for fid in sorted({f for html in [CLEAN] for f in []} | {
        "schema.duplicate_organization", "schema.duplicate_localbusiness", "schema.duplicate_website",
        "schema.conflicting_organization_name", "schema.conflicting_organization_url",
        "schema.conflicting_organization_logo", "schema.missing_id", "schema.duplicate_id_conflict",
        "schema.orphan_node", "schema.invalid_sameas", "schema.weak_sameas",
        "schema.article_missing_publisher", "schema.article_missing_author",
        "schema.website_missing_searchaction", "schema.breadcrumb_disconnected",
        "schema.canonical_mismatch", "schema.insecure_url", "schema.image_missing_dimensions",
        "schema.generic_type"}):
        assert knowledge.explain(fid) is not None, fid
