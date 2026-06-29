"""Tests for the static MCP usage guide (mcp_guide.usage_guide)."""

from __future__ import annotations

import re
from pathlib import Path

from astova_engine.mcp_guide import SUPPORTED_CLIENTS, usage_guide

_TOP_KEYS = {"client", "purpose", "recommended_entrypoints", "setup", "starter_prompt",
             "workflow", "safety_rules", "available_tools"}


def test_shape_generic():
    g = usage_guide()
    assert set(g) == _TOP_KEYS
    assert g["client"] == "generic"
    assert g["purpose"] and isinstance(g["purpose"], str)
    assert g["setup"] and g["workflow"] and g["starter_prompt"]


def test_recommended_entrypoints():
    g = usage_guide("generic")
    tools = [e["tool"] for e in g["recommended_entrypoints"]]
    assert tools == ["prepare_project_for_ai", "ai_ready_loop"]
    for e in g["recommended_entrypoints"]:
        assert e["when_to_use"]


def test_all_supported_clients():
    for c in SUPPORTED_CLIENTS:
        g = usage_guide(c)
        assert g["client"] == c
        assert g["setup"] and g["starter_prompt"]
    assert set(SUPPORTED_CLIENTS) == {"generic", "claude", "cursor", "chatgpt", "windsurf"}


def test_unknown_client_falls_back_to_generic():
    g = usage_guide("emacs")
    assert g["client"] == "generic"
    assert g == usage_guide("generic")


def test_chatgpt_is_url_first_repo_clients_use_prepare():
    assert "ai_ready_loop" in usage_guide("chatgpt")["starter_prompt"]
    for c in ("claude", "cursor", "windsurf"):
        assert "prepare_project_for_ai" in usage_guide(c)["starter_prompt"]


def test_safety_rules_present():
    rules = " ".join(usage_guide()["safety_rules"]).lower()
    for needle in ("invent facts", "author names", "sameas", "local-business",
                   "ask before", "verify_fix"):
        assert needle in rules, needle


def test_setup_includes_config_and_install():
    for c in SUPPORTED_CLIENTS:
        joined = " ".join(usage_guide(c)["setup"])
        assert "pip install" in joined
        assert "astova_engine.mcp_server" in joined


def test_available_tools_match_registered_mcp_tools():
    # Cross-check the guide's tool list against the actual @mcp.tool() functions, so adding a tool
    # without documenting it here fails the build.
    src = Path(__file__).resolve().parent.parent / "astova_engine" / "mcp_server.py"
    registered = set(re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)\(", src.read_text()))
    listed = {t["tool"] for t in usage_guide()["available_tools"]}
    assert listed == registered, f"guide vs registered drift: {listed ^ registered}"
    # every tool carries a non-empty one-line description
    for t in usage_guide()["available_tools"]:
        assert t["description"].strip()
