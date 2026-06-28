"""Tests for the pre-deploy project checks (project.py) — pure, offline."""

from __future__ import annotations

from damask_engine import project


def test_detect_framework():
    assert project.detect_framework({"next.config.js", "package.json"}) == ("nextjs", "public")
    assert project.detect_framework({"astro.config.mjs"}) == ("astro", "public")
    assert project.detect_framework({"wp-config.php"}) == ("wordpress", ".")
    assert project.detect_framework({"package.json"}) == ("node", "public")
    assert project.detect_framework({"index.html"}) == ("static", ".")


def test_robots_blocked_ai_detects_specific_and_wildcard():
    block_gptbot = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    assert project.robots_blocked_ai(block_gptbot) == ["GPTBot"]

    block_all = "User-agent: *\nDisallow: /\n"
    assert set(project.robots_blocked_ai(block_all)) == set(project.AI_CRAWLERS)

    allow_all = "User-agent: *\nAllow: /\n"
    assert project.robots_blocked_ai(allow_all) == []


def test_analyze_files_missing_all_yields_targeted_fixes():
    res = project.analyze_files(robots_txt=None, llms_txt=None, sitemap_xml=None, public_dir="public")
    assert res["status"] == {"robots": "missing", "llms": "missing", "sitemap": "missing"}
    by = {f["finding_id"]: f for f in res["fixes"]}
    assert by["project.robots_missing"]["target"] == "public/robots.txt"
    assert by["project.robots_missing"]["action"] == "create_file"
    assert by["project.llms_missing"]["target"] == "public/llms.txt"
    # every fix is agent-actionable
    for f in res["fixes"]:
        assert {"finding_id", "title", "action", "target", "instruction", "source"} <= set(f)


def test_analyze_files_blocked_ai_is_critical():
    res = project.analyze_files(
        robots_txt="User-agent: GPTBot\nDisallow: /\n",
        llms_txt="# site\n", sitemap_xml="<urlset><url><loc>x</loc></url></urlset>",
        public_dir=".",
    )
    assert res["status"]["robots"] == "blocks_ai"
    assert res["status"]["llms"] == "present"
    assert res["status"]["sitemap"] == "present"
    block = next(f for f in res["fixes"] if f["finding_id"] == "project.robots_blocks_ai")
    assert block["severity"] == "critical" and block["target"] == "robots.txt"


def test_analyze_files_root_public_dir_has_no_prefix():
    res = project.analyze_files(robots_txt=None, llms_txt=None, sitemap_xml=None, public_dir=".")
    by = {f["finding_id"]: f for f in res["fixes"]}
    assert by["project.robots_missing"]["target"] == "robots.txt"
