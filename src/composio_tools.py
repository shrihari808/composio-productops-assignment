"""
Composio Platform SDK integration for the 100-App Product Ops Research Agent.

Responsibilities:
1. Create a user-scoped Composio session (`composio.create(user_id=...)`).
2. Discover and execute live Composio catalog tools (e.g., `deepwiki_mcp` for
   open-source repo inspection, `hackernews`, or user-connected toolkits).
3. Cross-reference the 100 target apps against Composio's live toolkit catalog
   to capture existing Built Toolkits and Provider MCP (`_mcp`) siblings.
"""
from __future__ import annotations

import json
import os
from typing import Any
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

DEFAULT_USER_ID = "product_ops_researcher"


def get_composio_client() -> Composio:
    # Reads COMPOSIO_API_KEY automatically from the environment.
    return Composio()


def create_research_session(
    user_id: str = DEFAULT_USER_ID,
    toolkits: list[str] | None = None,
):
    composio = get_composio_client()
    if toolkits:
        return composio.create(user_id=user_id, toolkits=toolkits)
    return composio.create(user_id=user_id)


def run_first_real_tool_call() -> dict[str, Any]:
    """
    Discover a safe read-only catalog tool at runtime and execute it
    through a Composio session, returning the verified result and log_id.
    """
    session = create_research_session(
        user_id=DEFAULT_USER_ID,
        toolkits=["deepwiki_mcp", "hackernews"],
    )

    # 1. Runtime discovery via session.search()
    search_resp = session.search(query="read documentation structure of a github repository with deepwiki")
    search_dump = search_resp.model_dump(mode="json")

    primary_slugs: list[str] = []
    for r in search_dump.get("results", []):
        primary_slugs.extend(r.get("primary_tool_slugs", []))
    tool_schemas = search_dump.get("tool_schemas", {})

    print(f"Session ID: {session.session_id}")
    print(f"User ID: {DEFAULT_USER_ID}")
    print(f"Discovered tool slugs: {primary_slugs}")

    # Pick the first discovered tool that inspects repo structure or asks a question
    chosen_slug = None
    for slug in primary_slugs:
        if "STRUCTURE" in slug.upper() or "READ_WIKI" in slug.upper():
            chosen_slug = slug
            break
    if not chosen_slug and primary_slugs:
        chosen_slug = primary_slugs[0]

    schema = tool_schemas.get(chosen_slug, {})
    print(f"Chosen tool: {chosen_slug}")
    print(f"Input schema: {json.dumps(schema.get('input_schema', {}), indent=2)}")

    # Build arguments from the discovered schema dynamically
    props = schema.get("input_schema", {}).get("properties", {})
    args: dict[str, Any] = {}
    if "repoName" in props:
        args["repoName"] = "sherlock-project/sherlock"
    elif "repo_name" in props:
        args["repo_name"] = "sherlock-project/sherlock"
    elif "repository" in props:
        args["repository"] = "sherlock-project/sherlock"
    elif "url" in props:
        args["url"] = "https://github.com/sherlock-project/sherlock"

    # 2. Real execution via session.execute()
    exec_result = session.execute(chosen_slug, arguments=args)
    result_dump = exec_result.model_dump(mode="json")

    summary = {
        "session_id": session.session_id,
        "user_id": DEFAULT_USER_ID,
        "toolkit": "deepwiki_mcp",
        "tool_slug": chosen_slug,
        "arguments": args,
        "result_type": exec_result.result_type,
        "log_id": exec_result.log_id,
        "error": exec_result.error,
        "data_preview": str(result_dump.get("data", ""))[:600],
    }
    return summary


if __name__ == "__main__":
    out = run_first_real_tool_call()
    print("\n=== Verified Composio Tool Execution ===")
    print(json.dumps(out, indent=2))
