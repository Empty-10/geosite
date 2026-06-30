"""Shared JSON-LD parsing for the schema checks (onpage presence/validation + the deeper
schema_review). Pure: takes a parsed BeautifulSoup and returns the flattened object nodes.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup


def parse_nodes(soup: BeautifulSoup) -> list[dict]:
    """All JSON-LD object nodes on the page, flattening top-level lists and @graph containers."""
    out: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = list(data) if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
                out.append(node)
    return out


def node_types(node: dict) -> set[str]:
    """Lower-cased @type set for a node (handles a single type or a list)."""
    t = node.get("@type")
    if isinstance(t, list):
        return {str(x).lower() for x in t}
    return {str(t).lower()} if t else set()


def type_labels(node: dict) -> list[str]:
    """Original-case @type labels for evidence display."""
    t = node.get("@type")
    if isinstance(t, list):
        return [str(x) for x in t]
    return [str(t)] if t else []
