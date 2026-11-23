"""
Pattern Clustering & Product Ops Analytics Engine.

Consumes `final_results.json` (or `pass2_verified.json`), `pass1_results.json`,
`verification_diff_report.json`, `composio_catalog_deep.json`, and optional
`human_audit.json` to generate `data/analytics_summary.json` — the exact
single source of truth powering both the interactive HTML Case Study charts
and the agent-consumable summary.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def compute_analytics(
    final_records: list[dict[str, Any]],
    pass1_records: list[dict[str, Any]],
    diff_report: dict[str, Any],
    deep_catalog: dict[str, Any],
    human_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = len(final_records)

    auth_counts: Counter[str] = Counter()
    access_counts: Counter[str] = Counter()
    protocol_counts: Counter[str] = Counter()
    breadth_counts: Counter[str] = Counter()
    mcp_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    openapi_counts: Counter[str] = Counter()
    webhook_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()

    # Cross-tabs by category
    by_category: dict[str, dict[str, Any]] = {}
    categories_order: list[str] = []

    for r in final_records:
        cat = r["category"]
        if cat not in by_category:
            categories_order.append(cat)
            by_category[cat] = {
                "total": 0,
                "access_models": Counter(),
                "verdicts": Counter(),
                "mcp_official": 0,
                "mcp_community": 0,
                "oauth2_count": 0,
                "api_key_count": 0,
                "in_composio": 0,
                "not_in_composio": 0,
            }
        c = by_category[cat]
        c["total"] += 1
        c["access_models"][r["access_model"]] += 1
        c["verdicts"][r["buildability_verdict"]] += 1
        if r["mcp_status"] == "Official MCP":
            c["mcp_official"] += 1
        elif r["mcp_status"] == "Community MCP Only":
            c["mcp_community"] += 1
        if "OAuth2" in r["auth_methods"]:
            c["oauth2_count"] += 1
        if "API Key" in r["auth_methods"] or "Bearer Token" in r["auth_methods"]:
            c["api_key_count"] += 1
        if r.get("composio_catalog_slugs"):
            c["in_composio"] += 1
        else:
            c["not_in_composio"] += 1

        for am in r["auth_methods"]:
            auth_counts[am] += 1
        access_counts[r["access_model"]] += 1
        protocol_counts[r["api_protocol"]] += 1
        breadth_counts[r["api_breadth"]] += 1
        mcp_counts[r["mcp_status"]] += 1
        verdict_counts[r["buildability_verdict"]] += 1
        openapi_counts[r["openapi_spec_available"]] += 1
        webhook_counts[r["webhooks_supported"]] += 1
        confidence_counts[r["confidence"]] += 1
        coverage_counts[r.get("composio_coverage", "Not in Catalog")] += 1

    # Serialize category cross-tabs cleanly
    category_matrix = []
    for cat in categories_order:
        c = by_category[cat]
        self_serve_total = (
            c["access_models"]["Self-Serve Free / Trial"]
            + c["access_models"]["Self-Serve Paid Plan"]
        )
        gated_total = (
            c["access_models"]["Self-Serve Dev + App Review"]
            + c["access_models"]["Admin / Customer Account Required"]
            + c["access_models"]["Partner / Sales-Gated"]
        )
        category_matrix.append({
            "category": cat,
            "total": c["total"],
            "self_serve_count": self_serve_total,
            "gated_or_review_count": gated_total,
            "local_oss_count": c["access_models"]["Open-Source / Local Tool"],
            "ready_today": c["verdicts"]["Ready Today (Easy Win)"],
            "buildable_friction": c["verdicts"]["Buildable with Friction"],
            "gated_outreach": c["verdicts"]["Gated / Needs Outreach"],
            "blocked": c["verdicts"]["Blocked / Not API-Native"],
            "mcp_official": c["mcp_official"],
            "mcp_community": c["mcp_community"],
            "oauth2_count": c["oauth2_count"],
            "api_key_or_bearer_count": c["api_key_count"],
            "in_composio": c["in_composio"],
            "not_in_composio": c["not_in_composio"],
            "access_breakdown": dict(c["access_models"]),
        })

    # Strategic Composio Action Queues
    net_new_easy_wins = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "auth_methods": r["auth_methods"],
            "access_model": r["access_model"],
            "mcp_status": r["mcp_status"],
            "openapi": r["openapi_spec_available"],
        }
        for r in final_records
        if not r.get("composio_catalog_slugs")
        and r["buildability_verdict"] == "Ready Today (Easy Win)"
    ]
    net_new_friction = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "access_model": r["access_model"],
            "primary_blocker": r["primary_blocker"],
        }
        for r in final_records
        if not r.get("composio_catalog_slugs")
        and r["buildability_verdict"] == "Buildable with Friction"
    ]
    net_new_outreach = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "access_model": r["access_model"],
            "primary_blocker": r["primary_blocker"],
        }
        for r in final_records
        if not r.get("composio_catalog_slugs")
        and r["buildability_verdict"] == "Gated / Needs Outreach"
    ]
    net_new_blocked = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "api_protocol": r["api_protocol"],
            "primary_blocker": r["primary_blocker"],
        }
        for r in final_records
        if not r.get("composio_catalog_slugs")
        and r["buildability_verdict"] == "Blocked / Not API-Native"
    ]

    # Queue: Built-API-Only in Composio where vendor NOW ships an Official MCP!
    mcp_expansion_candidates = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "existing_slugs": r.get("composio_catalog_slugs", []),
            "mcp_evidence_url": r.get("mcp_evidence_url"),
        }
        for r in final_records
        if r.get("composio_coverage") == "Built API Only"
        and r["mcp_status"] == "Official MCP"
    ]

    # Queue: Webhooks supported by vendor, but 0 triggers currently in Composio!
    trigger_expansion_candidates = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "existing_slugs": r.get("composio_catalog_slugs", []),
            "tools_count": r.get("composio_tools_count", 0),
        }
        for r in final_records
        if r.get("composio_catalog_slugs")
        and r["webhooks_supported"] == "Yes"
        and int(r.get("composio_triggers_count") or 0) == 0
    ]

    # URL health totals
    url_stats = Counter()
    total_urls_checked = 0
    for r in final_records:
        for u, st in (r.get("url_health") or {}).items():
            total_urls_checked += 1
            if isinstance(st, int) and 200 <= st < 400:
                url_stats["ok_2xx_3xx"] += 1
            elif isinstance(st, int) and st in (403, 400, 429):
                url_stats["bot_shielded_403_429"] += 1
            elif isinstance(st, int) and st in (404, 410):
                url_stats["dead_404_410"] += 1
            else:
                url_stats["timeout_or_other"] += 1

    # GitHub audit stats
    github_audited = [r for r in final_records if r.get("github_mcp_audit") and not r["github_mcp_audit"].get("error")]

    # Multi-auth stats
    multi_auth_count = sum(1 for r in final_records if len(r["auth_methods"]) >= 2)
    oauth_and_apikey = sum(
        1
        for r in final_records
        if "OAuth2" in r["auth_methods"]
        and ("API Key" in r["auth_methods"] or "Bearer Token" in r["auth_methods"])
    )

    return {
        "total_apps": total,
        "distributions": {
            "auth_methods": dict(auth_counts.most_common()),
            "access_models": dict(access_counts.most_common()),
            "api_protocols": dict(protocol_counts.most_common()),
            "api_breadth": dict(breadth_counts.most_common()),
            "mcp_status": dict(mcp_counts.most_common()),
            "buildability_verdicts": dict(verdict_counts.most_common()),
            "openapi_spec_available": dict(openapi_counts.most_common()),
            "webhooks_supported": dict(webhook_counts.most_common()),
            "confidence": dict(confidence_counts.most_common()),
            "composio_coverage": dict(coverage_counts.most_common()),
        },
        "highlights": {
            "multi_auth_apps": multi_auth_count,
            "oauth_plus_key_or_token_apps": oauth_and_apikey,
            "self_serve_free_or_paid": access_counts["Self-Serve Free / Trial"] + access_counts["Self-Serve Paid Plan"],
            "gated_review_admin_or_partner": (
                access_counts["Self-Serve Dev + App Review"]
                + access_counts["Admin / Customer Account Required"]
                + access_counts["Partner / Sales-Gated"]
            ),
            "official_mcp_count": mcp_counts["Official MCP"],
            "community_mcp_count": mcp_counts["Community MCP Only"],
            "github_repos_audited_via_composio": len(github_audited),
            "total_urls_checked": total_urls_checked,
            "url_health_breakdown": dict(url_stats),
        },
        "category_matrix": category_matrix,
        "composio_roadmap": {
            "catalog_summary": deep_catalog.get("summary", {}),
            "net_new_easy_wins": net_new_easy_wins,
            "net_new_friction": net_new_friction,
            "net_new_outreach": net_new_outreach,
            "net_new_blocked": net_new_blocked,
            "mcp_expansion_candidates": mcp_expansion_candidates,
            "trigger_expansion_candidates": trigger_expansion_candidates,
        },
        "verification": {
            "pass2_diff_summary": {
                k: v for k, v in diff_report.items() if k != "diffs"
            },
            "sample_pass2_diffs": (diff_report.get("diffs") or [])[:30],
            "human_audit": human_audit or {},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute pattern clustering and analytics JSON")
    parser.add_argument("--final", type=str, default="data/final_results.json")
    parser.add_argument("--pass1", type=str, default="data/pass1_results.json")
    parser.add_argument("--diffs", type=str, default="data/verification_diff_report.json")
    parser.add_argument("--catalog", type=str, default="data/composio_catalog_deep.json")
    parser.add_argument("--human-audit", type=str, default="data/human_audit.json")
    parser.add_argument("--out", type=str, default="data/analytics_summary.json")
    args = parser.parse_args()

    final_path = ROOT / args.final
    if not final_path.exists():
        final_path = ROOT / "data/pass2_verified.json"
    final_records = json.loads(final_path.read_text(encoding="utf-8"))
    pass1_records = json.loads((ROOT / args.pass1).read_text(encoding="utf-8")) if (ROOT / args.pass1).exists() else []
    diff_report = json.loads((ROOT / args.diffs).read_text(encoding="utf-8")) if (ROOT / args.diffs).exists() else {}
    deep_catalog = json.loads((ROOT / args.catalog).read_text(encoding="utf-8")) if (ROOT / args.catalog).exists() else {}
    human_audit = json.loads((ROOT / args.human_audit).read_text(encoding="utf-8")) if (ROOT / args.human_audit).exists() else None

    summary = compute_analytics(final_records, pass1_records, diff_report, deep_catalog, human_audit)
    out_path = ROOT / args.out
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved analytics summary for {summary['total_apps']} apps to {out_path}")
    print(json.dumps(summary["distributions"], indent=2))
    print("Highlights:", json.dumps(summary["highlights"], indent=2))


if __name__ == "__main__":
    main()
