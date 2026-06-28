"""Small shared helpers for parsing."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_WS = re.compile(r"\s+")


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "lxml")


def visible_text(soup: BeautifulSoup) -> str:
    """Approximate the human-readable text: drop script/style/nav noise, collapse space."""
    clone = BeautifulSoup(str(soup), "lxml")
    for tag in clone(["script", "style", "noscript", "template"]):
        tag.decompose()
    body = clone.body or clone
    return _WS.sub(" ", body.get_text(" ", strip=True)).strip()


def word_count(text: str) -> int:
    return len(text.split()) if text else 0
