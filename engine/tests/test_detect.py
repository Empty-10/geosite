"""Fixture tests for bot-challenge detection (detect.detect_challenge / challenge_info).

One fixture per vendor's markers, plus clean-page negatives (no false positives) - including a
NORMAL site sitting behind Cloudflare, which must NOT be flagged.
"""

from __future__ import annotations

from astova_engine.detect import challenge_info, detect_challenge

URL = "https://mitel.com/"


# --------------------------------------------------------------------------- Cloudflare

def test_cloudflare_just_a_moment_403():
    assert detect_challenge(
        403, {"server": "cloudflare", "cf-ray": "8a1b2c"}, "Just a moment...",
        "Enable JavaScript and cookies to continue", URL,
    ) == "Cloudflare"


def test_cloudflare_challenge_platform_script_any_status():
    # The /cdn-cgi/challenge-platform script is challenge-specific even at 200.
    info = challenge_info(
        200, {"server": "cloudflare"}, "",
        '<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page"></script>', URL,
    )
    assert info and info["vendor"] == "Cloudflare" and info["marker"] == "challenge-platform"


def test_cloudflare_cf_mitigated_header():
    assert detect_challenge(403, {"cf-mitigated": "challenge", "cf-ray": "x"}, "", "", URL) == "Cloudflare"


def test_cloudflare_server_plus_cfray_on_blocked_status():
    # No body marker, but a 503 from cloudflare with cf-ray is a managed challenge.
    info = challenge_info(503, {"server": "cloudflare", "cf-ray": "abc"}, "", "", URL)
    assert info and info["vendor"] == "Cloudflare" and info["status"] == 503


def test_checking_your_browser():
    assert detect_challenge(503, {}, "Checking your browser before accessing", "", URL) == "Cloudflare"


# --------------------------------------------------------------------------- other vendors

def test_akamai_access_denied_403():
    assert detect_challenge(
        403, {"server": "AkamaiGHost"}, "Access Denied",
        "You don't have permission. Reference #18.abcd", URL,
    ) == "Akamai"


def test_perimeterx():
    assert detect_challenge(403, {}, "Access to this page has been denied",
                            "<div id='px-captcha'></div>", URL) == "PerimeterX/HUMAN"


def test_datadome_cookie():
    assert detect_challenge(403, {"set-cookie": "datadome=abc123; Path=/"}, "", "", URL) == "DataDome"


def test_imperva_incapsula():
    assert detect_challenge(403, {}, "", "Request unsuccessful. Incapsula incident ID: 1-2", URL) == "Imperva/Incapsula"


# --------------------------------------------------------------------------- no false positives

def test_clean_page_returns_none():
    assert detect_challenge(
        200, {"content-type": "text/html"}, "Acme - Pricing for teams",
        "Acme offers three plans. The Team plan is 12 dollars per seat per month.", URL,
    ) is None


def test_normal_site_behind_cloudflare_not_flagged():
    # 200, real content, Cloudflare headers + __cf_bm cookie -> a normal CF-fronted site, NOT a challenge.
    assert detect_challenge(
        200,
        {"server": "cloudflare", "cf-ray": "8a1b2c3d", "set-cookie": "__cf_bm=token; Path=/"},
        "Acme - AI infrastructure",
        "Acme builds developer tools used by thousands of engineering teams worldwide.",
        URL,
    ) is None


def test_access_denied_phrase_at_200_not_flagged():
    # A blog post that literally contains "access denied" at HTTP 200 must not trip Akamai detection.
    assert detect_challenge(
        200, {}, "How to fix Access Denied errors",
        "An Access Denied error means the server refused the request. Reference # your logs.", URL,
    ) is None


# --------------------------------------------------------------------------- shape

def test_challenge_info_shape_and_detect_returns_vendor_string():
    info = challenge_info(403, {}, "Just a moment...", "", URL)
    assert set(info) == {"vendor", "marker", "status"}
    assert info["vendor"] == "Cloudflare" and info["status"] == 403
    assert isinstance(detect_challenge(403, {}, "Just a moment...", "", URL), str)
    assert detect_challenge(200, {}, "Home", "real content here", URL) is None
