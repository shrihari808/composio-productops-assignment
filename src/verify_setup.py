"""
Verify setup for:
1. Composio Platform SDK (session creation, live tool discovery, and safe read-only tool execution)
2. Exa API (following build-with-exa skill conventions)
3. Google Gemini API (using GEMINI_MODEL from .env)

Never prints or logs API keys.
"""
from __future__ import annotations

import json
import os
from dotenv import load_dotenv

load_dotenv()


def check_env() -> None:
    required = ["COMPOSIO_API_KEY", "GEMINI_API_KEY", "GEMINI_MODEL", "EXA_API_KEY"]
    print("=== 1. Environment Check ===")
    for var in required:
        val = os.getenv(var)
        status = "SET" if val and len(val) > 5 else "MISSING"
        if var == "GEMINI_MODEL":
            print(f"  {var}: {val}")
        else:
            print(f"  {var}: {status}")


def check_composio() -> None:
    print("\n=== 2. Composio Platform SDK Check ===")
    from composio import Composio

    composio = Composio()
    user_id = "product_ops_researcher"
    session = composio.create(user_id=user_id)
    print(f"  Session created: session_id={session.session_id}")
    print(f"  MCP endpoint available: {bool(getattr(session, 'mcp', None))}")

    # Discover a safe, no-auth / read-only toolkit at runtime
    toolkits_res = session.toolkits(limit=20)
    items = getattr(toolkits_res, "items", [])
    print(f"  Sample toolkits returned: {len(items)}")

    # Search for a safe read-only tool via session.search()
    search_res = session.search(query="search hackernews or wikipedia or web search without auth")
    print("  Search response type:", type(search_res).__name__)
    dump = search_res.model_dump(mode="json") if hasattr(search_res, "model_dump") else str(search_res)
    if isinstance(dump, dict):
        # Print tool slugs discovered without dumping huge schemas
        results = dump.get("results") or dump.get("data") or dump
        print("  Search keys:", list(dump.keys()))
        # Check toolkit connection statuses
        statuses = dump.get("toolkit_connection_statuses") or []
        print(f"  Toolkit statuses found: {len(statuses)}")
        for s in statuses[:5]:
            print(f"    - toolkit={s.get('toolkit')} has_active={s.get('has_active_connection')} instant={bool(s.get('instant_account'))}")
        # Inspect discovered tool slugs
        main_tools = dump.get("results", [{}])[0].get("primary_tool_slugs", []) if isinstance(dump.get("results"), list) and dump.get("results") else []
        print(f"  Primary tool slugs: {main_tools[:8]}")

    # Also inspect live catalog for a few no-auth toolkits (e.g., hackernews, composio_search)
    for query_name in ["hackernews", "exa", "firecrawl", "github"]:
        tk = session.toolkits(search=query_name, limit=5)
        tk_items = getattr(tk, "items", [])
        summary = [
            {
                "slug": getattr(i, "slug", None),
                "is_no_auth": getattr(i, "is_no_auth", None),
                "connected": getattr(getattr(i, "connection", None), "is_active", None),
            }
            for i in tk_items
        ]
        print(f"  Catalog lookup '{query_name}': {summary}")


def check_exa() -> None:
    print("\n=== 3. Exa API Check ===")
    from exa_py import Exa

    exa = Exa()  # reads EXA_API_KEY from environment
    result = exa.search(
        "HubSpot API authentication documentation",
        type="auto",
        objective="Find the official HubSpot API authentication documentation page and check what auth methods it supports.",
        contents={"highlights": True},
    )
    print(f"  Exa returned {len(result.results)} results")
    for item in result.results[:3]:
        hl = (item.highlights[0][:120] + "...") if getattr(item, "highlights", None) else "(no highlight)"
        print(f"    - {item.title} | {item.url}")
        print(f"      highlight: {hl}")


def check_gemini() -> None:
    print("\n=== 4. Gemini API Check ===")
    from google import genai

    model_name = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=model_name,
        contents="Reply with exactly one JSON object: {\"status\": \"ok\", \"model_ack\": true}",
    )
    print(f"  Model '{model_name}' response: {resp.text.strip()}")


if __name__ == "__main__":
    check_env()
    try:
        check_composio()
    except Exception as e:
        print(f"  [COMPOSIO ERROR] {type(e).__name__}: {e}")
    try:
        check_exa()
    except Exception as e:
        print(f"  [EXA ERROR] {type(e).__name__}: {e}")
    try:
        check_gemini()
    except Exception as e:
        print(f"  [GEMINI ERROR] {type(e).__name__}: {e}")
