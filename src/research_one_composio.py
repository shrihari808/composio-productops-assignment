"""
Upgrade 3: Runnable Single-App Live Research Demo powered end-to-end by Composio Sessions.

Demonstrates how a reviewer or agent can research ANY single app directly through
Composio's Platform SDK (`session.search()` + `session.execute()`), routing live
tool calls through Composio (`exa` + `deepwiki_mcp` + `github`) so every call
produces an auditable `session_id` and `log_id` in the Composio Dashboard.

Usage:
  python src/research_one_composio.py --app "Stripe"
  python src/research_one_composio.py --app "Sherlock"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from composio import Composio

from llm_utils import generate_content_throttled
from research_agent import GITHUB_REPO_HINTS, LLMAppAnalysis
from schema import AppResearchRecord

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
APPS_PATH = ROOT / "data" / "apps.json"
DEEP_CATALOG_PATH = ROOT / "data" / "composio_catalog_deep.json"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def discover_first_tool(session: Any, query: str, preferred_tokens: list[str]) -> tuple[str | None, dict]:
    sr = session.search(query=query)
    dump = sr.model_dump(mode="json")
    slugs: list[str] = []
    for r in dump.get("results", []):
        slugs.extend(r.get("primary_tool_slugs", []))
    schemas = dump.get("tool_schemas", {})
    for token in preferred_tokens:
        for s in slugs:
            if token in s.upper():
                return s, schemas.get(s, {})
    if slugs:
        return slugs[0], schemas.get(slugs[0], {})
    return None, {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-App Live Research Runner via Composio Session")
    parser.add_argument("--app", type=str, required=True, help="App name (e.g. 'Stripe', 'HubSpot', 'Sherlock')")
    args = parser.parse_args()

    apps = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    match = next((a for a in apps if a["name"].lower() == args.app.lower()), None)
    if not match:
        match = {"id": 0, "name": args.app, "category": "Custom Query", "hint": args.app}

    deep_catalog = {}
    if DEEP_CATALOG_PATH.exists():
        deep_catalog = json.loads(DEEP_CATALOG_PATH.read_text(encoding="utf-8")).get("by_app", {})
    cat_info = deep_catalog.get(match["name"], {})

    t0 = time.time()
    composio = Composio()
    session = composio.create(
        user_id="product_ops_researcher",
        toolkits=["exa", "deepwiki_mcp", "github"],
    )
    print(f"=== Composio Live Research Runner ===")
    print(f"App: {match['name']} ({match['hint']})")
    print(f"Composio Session ID: {session.session_id}")

    # Check active connections
    tk_page = session.toolkits(toolkits=["exa", "deepwiki_mcp", "github"])
    active = {
        i.slug: bool(getattr(getattr(i, "connection", None), "is_active", False)) or bool(getattr(i, "is_no_auth", False))
        for i in tk_page.items
    }
    print(f"Toolkit readiness: {active}")

    logs: list[dict[str, Any]] = []
    evidence_blocks: list[str] = []

    # 1. Execute Exa Search via Composio's `exa` toolkit (if connected)
    if active.get("exa"):
        exa_slug, exa_schema = discover_first_tool(
            session,
            "search the web using exa with highlights",
            ["EXA_SEARCH"],
        )
        if exa_slug:
            props = (exa_schema.get("input_schema") or {}).get("properties", {})
            q1 = f"{match['name']} ({match['hint']}) official API documentation authentication OAuth API key MCP server"
            call_args: dict[str, Any] = {"query": q1}
            if "type" in props:
                call_args["type"] = "auto"
            if "contents" in props:
                call_args["contents"] = {"highlights": True}
            res = session.execute(exa_slug, arguments=call_args)
            dump = res.model_dump(mode="json")
            logs.append({
                "toolkit": "exa",
                "tool_slug": exa_slug,
                "result_type": res.result_type,
                "log_id": res.log_id,
            })
            evidence_blocks.append(f"=== COMPOSIO EXA TOOL ({exa_slug}, log_id={res.log_id}) ===\n{json.dumps(dump.get('data'), default=str)[:5000]}")
            print(f"  [Composio -> {exa_slug}] result_type={res.result_type} log_id={res.log_id}")
    else:
        print("  [NOTE] Composio `exa` toolkit is not connected yet. Run `python src/connect_integrations.py --toolkits exa` to connect it.")

    # 2. Execute DeepWiki MCP via Composio if open-source repo applies
    repo = GITHUB_REPO_HINTS.get(match["name"])
    if repo and active.get("deepwiki_mcp"):
        dw_slug, _ = discover_first_tool(
            session,
            "read wiki documentation structure of a github repository",
            ["READ_WIKI_STRUCTURE"],
        )
        if dw_slug:
            res = session.execute(dw_slug, arguments={"repoName": repo})
            dump = res.model_dump(mode="json")
            logs.append({
                "toolkit": "deepwiki_mcp",
                "tool_slug": dw_slug,
                "result_type": res.result_type,
                "log_id": res.log_id,
            })
            evidence_blocks.append(f"=== COMPOSIO DEEPWIKI MCP ({dw_slug}, log_id={res.log_id}) ===\n{str(dump.get('data'))[:2500]}")
            print(f"  [Composio -> {dw_slug}] result_type={res.result_type} log_id={res.log_id}")

    # 3. Execute GitHub Repo Audit via Composio if connected and repo applies
    if repo and active.get("github"):
        from composio_github import ComposioGitHubAuditor

        auditor = ComposioGitHubAuditor(session)
        owner, rname = repo.split("/", 1)
        gh_res = auditor.audit_repo(owner, rname)
        if gh_res:
            logs.append({
                "toolkit": "github",
                "tool_slug": gh_res.get("tool_slug"),
                "result_type": gh_res.get("result_type"),
                "log_id": gh_res.get("composio_log_id"),
            })
            evidence_blocks.append(f"=== COMPOSIO GITHUB AUDIT ===\n{json.dumps(gh_res, indent=2)}")
            print(f"  [Composio -> {gh_res.get('tool_slug')}] result_type={gh_res.get('result_type')} log_id={gh_res.get('composio_log_id')}")

    if not evidence_blocks:
        raise SystemExit("No live Composio evidence returned (connect `exa` first via `python src/connect_integrations.py --toolkits exa,github`).")

    # 4. Synthesize structured verdict using Gemini
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""Analyze `{match['name']}` ({match['hint']}) for Composio AI agent toolkit buildability strictly from the live Composio tool outputs below.
Live Composio Catalog Metadata: {json.dumps(cat_info, indent=2)[:1500]}

EVIDENCE:
{chr(10).join(evidence_blocks)}
"""
    resp = generate_content_throttled(
        gemini_client,
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMAppAnalysis,
            temperature=0.1,
        ),
    )
    parsed = LLMAppAnalysis.model_validate_json(resp.text)
    record = AppResearchRecord(
        id=match["id"],
        name=match["name"],
        category=match["category"],
        hint=match["hint"],
        **parsed.model_dump(),
        composio_catalog_slugs=cat_info.get("all_slugs", []),
        composio_coverage=cat_info.get("coverage", "Not in Catalog"),
        composio_tools_count=cat_info.get("total_tools_count", 0),
        composio_triggers_count=cat_info.get("total_triggers_count", 0),
        composio_auth_modes=cat_info.get("auth_modes", []),
        composio_managed_auth=bool(cat_info.get("composio_managed_auth_schemes")),
        composio_logo=cat_info.get("logo"),
    )

    elapsed = round(time.time() - t0, 2)
    print(f"\n=== Completed in {elapsed}s | Composio Audit Logs ===")
    print(json.dumps(logs, indent=2))
    print("\n=== Structured Verdict ===")
    print(record.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
