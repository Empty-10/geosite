"""Bot-challenge / interstitial detection.

When a scan hits a Cloudflare / Akamai / DataDome / PerimeterX / Imperva interstitial instead of the
real page, the HTML we'd score is the challenge holding page (its own noindex, ~0 words) - not the
site. `detect_challenge()` spots that so the engine can flag the result as UNRELIABLE rather than
present a confident-but-wrong scorecard (the accuracy principle).

Pure and fixture-testable: takes the fetched status, response headers, page title, visible text and
final URL; returns the vendor (or None). No network, no parsing - just signal matching.
"""

from __future__ import annotations

# Status codes a challenge/block page is typically served with.
_BLOCKED_STATUS = (403, 503)

# Cloudflare interstitial markers - strings that appear on the "Just a moment" / managed-challenge
# page (title, body, or the /cdn-cgi/challenge-platform script) but not on real content. Kept narrow
# on purpose: the bare `__cf` cookie prefix is deliberately NOT used, because `__cf_bm` /
# `__cf_clearance` cookies are set on NORMAL Cloudflare-fronted sites and would false-positive.
_CF_MARKERS = (
    "just a moment",
    "checking your browser",
    "enable javascript and cookies to continue",
    "performing security verification",
    "challenge-platform",
    "cf-chl",
    "_cf_chl",
    "__cf_chl",
)

# Vendor markers found in the body, title, or a Set-Cookie header. Specific enough to match alone.
_COOKIE_OR_BODY = {
    "PerimeterX/HUMAN": ("px-captcha",),
    "DataDome": ("datadome",),
    "Imperva/Incapsula": ("_incapsula_", "incapsula incident"),
}

# Akamai uses generic phrases ("Access Denied", "Reference #...") that could appear in real content,
# so they only count alongside a blocked status.
_AKAMAI_MARKERS = ("access denied", "reference #")


def challenge_info(
    status: int,
    headers: dict | None,
    title: str | None,
    text: str | None,
    final_url: str | None,
) -> dict | None:
    """Return {"vendor", "marker", "status"} when the response looks like a bot-protection
    challenge/interstitial, else None. Pure."""
    h = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    blob = " ".join([title or "", text or "", final_url or ""]).lower()
    cookies = h.get("set-cookie", "")
    blocked = status in _BLOCKED_STATUS

    # --- Cloudflare ---
    for mk in _CF_MARKERS:
        if mk in blob:
            return {"vendor": "Cloudflare", "marker": mk, "status": status}
    if "cf-mitigated" in h:
        return {"vendor": "Cloudflare", "marker": "cf-mitigated header", "status": status}
    if blocked and h.get("server", "").startswith("cloudflare") and "cf-ray" in h:
        return {"vendor": "Cloudflare", "marker": f"server=cloudflare + cf-ray + HTTP {status}",
                "status": status}

    # --- PerimeterX / DataDome / Imperva (specific body or cookie markers) ---
    for vendor, marks in _COOKIE_OR_BODY.items():
        for mk in marks:
            if mk in blob or mk in cookies:
                return {"vendor": vendor, "marker": mk, "status": status}

    # --- Akamai (generic phrases require a blocked status to avoid false positives) ---
    if blocked:
        for mk in _AKAMAI_MARKERS:
            if mk in blob:
                return {"vendor": "Akamai", "marker": mk, "status": status}

    return None


def detect_challenge(
    status: int,
    headers: dict | None,
    title: str | None,
    text: str | None,
    final_url: str | None,
) -> str | None:
    """The detected bot-protection vendor (e.g. "Cloudflare"), or None if the page looks real."""
    info = challenge_info(status, headers, title, text, final_url)
    return info["vendor"] if info else None
