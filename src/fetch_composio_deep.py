"""
Upgrade 1: Deep Live Composio Catalog Audit.

Fetches rich production metadata from `/api/v3.1/toolkits/{slug}` for every
matched toolkit across the 100 target apps:
- toolkit_type ("api" vs "mcp")
- auth_modes (from auth_config_details)
- composio_managed_auth_schemes
- tools_count & triggers_count
- version, updated_at, logo URL

Saves enriched catalog intelligence to `data/composio_catalog_deep.json`
for both Pass 2 ground-truth cross-verification and the executive roadmap.
"""
from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from composio import Composio

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
MATCH_PATH = ROOT / "data" / "composio_catalog_match.json"
OUT_PATH = ROOT / "data" / "composio_catalog_deep.json"


def fetch_toolkit_detail(composio: Composio, slug: str) -> dict[str, Any]:
    try:
        r = composio.client.get(f"/api/v3.1/toolkits/{slug}", cast_to=object)
        if not isinstance(r, dict):
            return {"slug": slug, "error": "Unexpected response type"}
        meta = r.get("meta") or {}
        auth_details = r.get("auth_config_details") or []
        auth_modes = []
        for a in auth_details:
            mode = a.get("mode") if isinstance(a, dict) else None
            if mode and mode not in auth_modes:
                auth_modes.append(mode)
        return {
            "slug": r.get("slug", slug),
            "name": r.get("name"),
            "toolkit_type": r.get("toolkit_type"),  # "api" or "mcp"
            "enabled": r.get("enabled"),
            "deprecated": r.get("deprecated"),
            "auth_modes": auth_modes,
            "composio_managed_auth_schemes": r.get("composio_managed_auth_schemes") or [],
            "tools_count": meta.get("tools_count", 0),
            "triggers_count": meta.get("triggers_count", 0),
            "version": meta.get("version"),
            "updated_at": meta.get("updated_at"),
            "logo": meta.get("logo"),
            "app_url": meta.get("app_url"),
            "docs_url": r.get("docs_url"),
            "auth_guide_url": r.get("auth_guide_url"),
        }
    except Exception as e:
        return {"slug": slug, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    match_data = json.loads(MATCH_PATH.read_text(encoding="utf-8"))
    matches: dict[str, list[dict]] = match_data["matches"]

    # Also add mermaid_chart_mcp as a related match note for Mermaid CLI? Keep exact matches strictly accurate.
    all_slugs: list[str] = sorted({
        tk["slug"]
        for tks in matches.values()
        for tk in tks
        if tk.get("slug")
    })
    print(f"Fetching deep /api/v3.1/toolkits/{{slug}} metadata for {len(all_slugs)} matched toolkits...", flush=True)

    composio = Composio()
    details_by_slug: dict[str, dict[str, Any]] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(fetch_toolkit_detail, composio, s): s for s in all_slugs}
        for idx, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            slug = futs[fut]
            res = fut.result()
            details_by_slug[slug] = res
            if idx % 20 == 0 or idx == len(all_slugs):
                print(f"  Fetched {idx}/{len(all_slugs)} toolkits...", flush=True)

    enriched_by_app: dict[str, dict[str, Any]] = {}
    summary = {
        "total_composio_toolkits_scanned": match_data["total_composio_toolkits_scanned"],
        "apps_matched": 0,
        "apps_not_in_composio": 0,
        "built_api_only": 0,
        "provider_mcp_only": 0,
        "both_built_and_mcp": 0,
        "with_composio_managed_oauth": 0,
        "with_triggers": 0,
        "total_tools_across_matched": 0,
    }

    for app_name, tks in matches.items():
        enriched_list = [details_by_slug[t["slug"]] for t in tks if t.get("slug") in details_by_slug]
        api_slugs = [d["slug"] for d in enriched_list if d.get("toolkit_type") == "api"]
        mcp_slugs = [d["slug"] for d in enriched_list if d.get("toolkit_type") == "mcp"]
        all_auth_modes = sorted({m for d in enriched_list for m in (d.get("auth_modes") or [])})
        managed_schemes = sorted({m for d in enriched_list for m in (d.get("composio_managed_auth_schemes") or [])})
        total_tools = sum(int(d.get("tools_count") or 0) for d in enriched_list)
        total_triggers = sum(int(d.get("triggers_count") or 0) for d in enriched_list)
        logo = next((d.get("logo") for d in enriched_list if d.get("logo")), None)

        if not enriched_list:
            coverage = "Not in Catalog"
            summary["apps_not_in_composio"] += 1
        elif api_slugs and mcp_slugs:
            coverage = "Both Built + Provider MCP"
            summary["apps_matched"] += 1
            summary["both_built_and_mcp"] += 1
        elif mcp_slugs:
            coverage = "Provider MCP Only"
            summary["apps_matched"] += 1
            summary["provider_mcp_only"] += 1
        else:
            coverage = "Built API Only"
            summary["apps_matched"] += 1
            summary["built_api_only"] += 1

        if managed_schemes:
            summary["with_composio_managed_oauth"] += 1
        if total_triggers > 0:
            summary["with_triggers"] += 1
        summary["total_tools_across_matched"] += total_tools

        enriched_by_app[app_name] = {
            "coverage": coverage,
            "api_slugs": api_slugs,
            "mcp_slugs": mcp_slugs,
            "all_slugs": [d["slug"] for d in enriched_list],
            "auth_modes": all_auth_modes,
            "composio_managed_auth_schemes": managed_schemes,
            "total_tools_count": total_tools,
            "total_triggers_count": total_triggers,
            "logo": logo,
            "toolkits": enriched_list,
        }

    out = {"summary": summary, "by_app": enriched_by_app}
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n=== Deep Composio Catalog Audit Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
