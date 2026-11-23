"""
Pass 2 Verification Loop — Automated Fact-Checking, Link Auditing & Disconfirmation Agent.

Catches and corrects Pass 1 errors using three verification mechanisms:
1. Live HTTP link health audit across all `evidence_urls` and `mcp_evidence_url`.
2. Exa `/contents` live extraction (checking `statuses`, per `build-with-exa` skill)
   plus targeted disconfirmation `/search` queries for hidden access gates,
   paywalls, app-review requirements, and official vendor MCP servers.
3. Gemini Critic Agent (`gemini-4-hydrogen`) that audits every Pass 1 claim
   against the freshly extracted primary-source text and logs field-level diffs.

Usage:
  python src/verify_agent.py --input data/pass1_results.json --output data/pass2_verified.json --all
  python src/verify_agent.py --input data/pass1_results.json --output data/pass2_verified.json --ids 2,10,28,58,92
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from exa_py import Exa
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from composio import Composio
from composio_github import ComposioGitHubAuditor
from llm_utils import generate_content_throttled
from schema import (
    AccessModel,
    ApiBreadth,
    ApiProtocol,
    AppResearchRecord,
    AuthMethod,
    BuildabilityVerdict,
    ConfidenceLevel,
    McpStatus,
)

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "composio_catalog_match.json"
DEEP_CATALOG_PATH = ROOT / "data" / "composio_catalog_deep.json"
DIFF_REPORT_PATH = ROOT / "data" / "verification_diff_report.json"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class FieldChange(BaseModel):
    field: str = Field(description="Name of the corrected field.")
    old_value: str = Field(description="Original Pass 1 value.")
    new_value: str = Field(description="Corrected Pass 2 value.")
    reason: str = Field(description="Primary-source evidence explaining why Pass 1 was wrong or incomplete.")


class CriticVerdict(BaseModel):
    one_liner: str
    auth_methods: list[AuthMethod]
    auth_notes: str
    access_model: AccessModel
    access_notes: str
    api_protocol: ApiProtocol
    api_breadth: ApiBreadth
    api_surface_notes: str
    mcp_status: McpStatus
    mcp_evidence_url: str | None = None
    openapi_spec_available: Literal["Yes", "No", "Unknown"]
    webhooks_supported: Literal["Yes", "No", "Unknown"]
    buildability_verdict: BuildabilityVerdict
    primary_blocker: str
    evidence_urls: list[str] = Field(min_length=1)
    confidence: ConfidenceLevel
    changes_made: list[FieldChange] = Field(
        default_factory=list,
        description="Exact list of substantive corrections made compared to Pass 1. Empty if Pass 1 was already accurate.",
    )


def check_url_health(url: str) -> int | str:
    try:
        with httpx.Client(follow_redirects=True, timeout=6.0, headers=HEADERS) as client:
            resp = client.head(url)
            if resp.status_code in (405, 403, 400):
                resp = client.get(url)
            return resp.status_code
    except Exception as e:
        return f"ERR:{type(e).__name__}"


def check_record_urls(record: dict[str, Any]) -> dict[str, int | str]:
    urls = list(record.get("evidence_urls") or [])
    if record.get("mcp_evidence_url"):
        urls.append(record["mcp_evidence_url"])
    unique_urls = list(dict.fromkeys(u for u in urls if u))
    health: dict[str, int | str] = {}
    for u in unique_urls:
        health[u] = check_url_health(u)
    return health


def extract_live_contents(exa: Exa, urls: list[str]) -> tuple[str, dict[str, str]]:
    """
    Use Exa `/contents` with top-level `text=True` and inspect `statuses`
    per the `build-with-exa` skill guidelines.
    """
    if not urls:
        return "(no URLs provided)", {}
    statuses_map: dict[str, str] = {}
    chunks: list[str] = []
    try:
        resp = exa.get_contents(urls[:3], text={"max_characters": 3500})
        for st in getattr(resp, "statuses", None) or []:
            sid = getattr(st, "id", None) or (st.get("id") if isinstance(st, dict) else None)
            sval = getattr(st, "status", None) or (st.get("status") if isinstance(st, dict) else None)
            if sid:
                statuses_map[str(sid)] = str(sval)
        for item in getattr(resp, "results", None) or []:
            u = getattr(item, "url", "")
            title = getattr(item, "title", "")
            txt = (getattr(item, "text", "") or "")[:3500]
            chunks.append(f"LIVE PAGE TITLE: {title}\nURL: {u}\nEXTRACTED TEXT:\n{txt}")
    except Exception as e:
        return f"(exa.get_contents failed: {type(e).__name__}: {e})", statuses_map
    return "\n\n===\n\n".join(chunks) if chunks else "(no text extracted)", statuses_map


def run_disconfirmation_search(exa: Exa, name: str, hint: str, pass1: dict[str, Any]) -> str:
    """
    Run a targeted Exa `/search` specifically designed to catch Pass 1 blind spots:
    - Paid-plan gates, partner approvals, app review requirements
    - Official vendor MCP servers or newly shipped public APIs
    """
    q = f"{name} ({hint}) API pricing plan requirement approval partner OR official MCP server"
    obj = (
        f"Verify and stress-test claims about {name}'s API access and MCP support. "
        "Look specifically for whether API access requires a paid tier, enterprise contract, "
        "partner approval, or app review, and verify if an official vendor-maintained MCP server exists."
    )
    res = exa.search(
        q,
        type="auto",
        objective=obj,
        contents={"highlights": True},
    )
    blocks: list[str] = []
    for item in (getattr(res, "results", None) or [])[:5]:
        u = getattr(item, "url", "")
        t = getattr(item, "title", "")
        hl = "\n".join((getattr(item, "highlights", None) or [])[:3])
        blocks.append(f"TITLE: {t}\nURL: {u}\nHIGHLIGHTS:\n{hl}")
    return "\n\n---\n\n".join(blocks)


def verify_single_record(
    record: dict[str, Any],
    exa: Exa,
    gemini_client: genai.Client,
    deep_catalog_by_app: dict[str, dict[str, Any]],
    github_auditor: ComposioGitHubAuditor | None = None,
) -> tuple[AppResearchRecord, list[dict[str, Any]]]:
    name = record["name"]
    hint = record["hint"]

    # 1. Live URL HTTP check
    url_health = check_record_urls(record)
    # Only 404/410 are definitively dead; 403/400/429/timeouts are often bot-shielded doc portals
    broken_urls = [u for u, st in url_health.items() if isinstance(st, int) and st in (404, 410)]

    # 2. Extract live primary-source doc text via Exa `/contents`
    candidate_urls = [u for u in (record.get("evidence_urls") or []) if u not in broken_urls]
    if record.get("mcp_evidence_url") and record["mcp_evidence_url"] not in broken_urls:
        candidate_urls.append(record["mcp_evidence_url"])
    live_text, exa_statuses = extract_live_contents(exa, candidate_urls[:3])

    # Also mark URLs as dead if BOTH httpx failed (non-200/300) AND Exa /contents failed
    for u, st in url_health.items():
        if u not in broken_urls and exa_statuses.get(u) == "error":
            if not (isinstance(st, int) and 200 <= st < 400):
                broken_urls.append(u)

    # 3. Targeted disconfirmation search via Exa `/search`
    disconfirm_text = run_disconfirmation_search(exa, name, hint, record)

    # 4. Upgrade 1: Deep Live Composio Catalog Ground Truth (/api/v3.1/toolkits/{slug})
    cat_info = deep_catalog_by_app.get(name, {})
    catalog_slugs = cat_info.get("all_slugs", [])
    catalog_ground_truth = {
        "coverage": cat_info.get("coverage", "Not in Catalog"),
        "api_slugs": cat_info.get("api_slugs", []),
        "mcp_slugs": cat_info.get("mcp_slugs", []),
        "composio_production_auth_modes": cat_info.get("auth_modes", []),
        "composio_managed_oauth_schemes": cat_info.get("composio_managed_auth_schemes", []),
        "tools_count": cat_info.get("total_tools_count", 0),
        "triggers_count": cat_info.get("total_triggers_count", 0),
    }

    # 5. Upgrade 2: Live GitHub MCP / Open-Source Repo Audit via Composio `github` toolkit
    github_audit: dict[str, Any] | None = None
    if github_auditor and github_auditor.enabled:
        gh_urls: list[str] = []
        if record.get("mcp_evidence_url"):
            gh_urls.append(record["mcp_evidence_url"])
        gh_urls.extend(record.get("evidence_urls") or [])
        repo_pair = github_auditor.extract_github_repo(gh_urls)
        if repo_pair:
            github_audit = github_auditor.audit_repo(repo_pair[0], repo_pair[1])

    # 6. Gemini Critic Agent
    critic_prompt = f"""You are a rigorous AI Product Ops QA Auditor verifying a Pass 1 research record for `{name}` ({hint}).
Your job is to catch hallucinations, broken links, missed paywalls/app reviews, auth discrepancies, and wrong MCP classifications using ONLY the fresh primary-source evidence below.

PASS 1 RECORD TO AUDIT:
{json.dumps({k: v for k, v in record.items() if k not in ('url_health', 'verification_changes', 'human_audited', 'github_mcp_audit')}, indent=2)}

LIVE URL HEALTH CHECK RESULTS:
{json.dumps(url_health, indent=2)}

EXA /CONTENTS EXTRACTION STATUSES:
{json.dumps(exa_statuses, indent=2)}

LIVE EXTRACTED DOC TEXT (FROM EXA /CONTENTS):
{live_text}

DISCONFIRMATION SEARCH RESULTS (GATING, PRICING, REVIEW, OFFICIAL MCP):
{disconfirm_text}

LIVE COMPOSIO PRODUCTION CATALOG GROUND TRUTH (`/api/v3.1/toolkits`):
{json.dumps(catalog_ground_truth, indent=2)}

{f"LIVE GITHUB REPO AUDIT (VIA COMPOSIO GITHUB TOOLKIT):{chr(10)}{json.dumps(github_audit, indent=2)}" if github_audit else ""}

STRICT AUDITING CHECKLIST:
1. BROKEN URLS: ONLY remove a URL if it returned HTTP 404/410 OR failed both HTTP check AND Exa `/contents`. Do NOT delete valid English official docs just because a bot-shielded portal (e.g. Meta, LinkedIn, Cloudflare) returned 403/400/timeout to a raw HTTP check. NEVER prefer non-English localized URLs (like `?locale=zh_CN`) over English official docs.
2. COMPOSIO CATALOG CROSS-CHECK:
   - Compare Pass 1's `auth_methods` against `composio_production_auth_modes` (e.g., if Composio production catalog shows `OAUTH2` or `DCR_OAUTH` or `API_KEY` and official docs confirm it, make sure Pass 1 didn't miss that auth method!).
   - If `mcp_slugs` is non-empty (a Composio Provider MCP `*_mcp` exists in production), double-check if the vendor indeed publishes an official remote MCP server and ensure `mcp_status` reflects the primary evidence accurately.
3. GITHUB REPO AUDIT CHECK (if present above):
   - Use `owner_login`, `owner_type` (`Organization` vs `User`), `stars`, `archived`, and `pushed_at` to verify whether a cited GitHub MCP repo is genuinely vendor-official (`Official MCP`) vs. a third-party/community repo (`Community MCP Only`) or archived/unmaintained.
4. ACCESS MODEL PRECISION (most common Pass 1 mistake!):
   - Does the doc say API access is only on Pro/Business/Enterprise paid plans? -> `Self-Serve Paid Plan` (NOT `Self-Serve Free / Trial`).
   - Does production access require App Review, Business Verification, Developer Token approval, or Marketplace review (e.g., Google Ads, Meta Ads, Threads, WhatsApp, LinkedIn Ads, Pinterest, Amazon SP-API, Shopify public apps)? -> `Self-Serve Dev + App Review`.
   - Does it require an existing paying customer admin account with no free dev sandbox (e.g., Gladly, Gorgias, Brex, Ramp, Pylon)? -> `Admin / Customer Account Required` or `Partner / Sales-Gated`.
   - Does it require contacting sales / enterprise partnership to get API access or docs (e.g., DealCloud, PitchBook, Salesforce Commerce Cloud, NotebookLM Enterprise)? -> `Partner / Sales-Gated`.
5. MCP STATUS & ENTITY CONFUSION PRECISION:
   - ENTITY CHECK: Verify that every evidence URL and `mcp_evidence_url` actually belongs to `{name}` (`{hint}`) and NOT a similarly-named company or unrelated package (e.g. Paygent Connect != Payman AI, fanbasis != unrelated npm packages, Mermaid CLI != commercial Mermaid Chart SaaS). If Pass 1 mixed up entities, fix all affected fields and log the change!
   - Mark `Official MCP` ONLY if the vendor itself publishes/documents an official MCP server for THIS exact product on its own domain or verified vendor GitHub organization. An OpenAPI spec URL or third-party wrapper is NOT an Official MCP. Always provide a working `mcp_evidence_url` when `mcp_status != "None Found"`, and set `mcp_evidence_url` to `null` if `mcp_status == "None Found"`.
   - If Pass 1 missed an official MCP server that fresh search confirms, UPGRADE it to `Official MCP` and log the change!
   - If Pass 1 cited a third-party repo, wrong company, or non-MCP page as `Official MCP`, DOWNGRADE it to `Community MCP Only` or `None Found`!
6. VERDICT CONSISTENCY & AUTH PRECISION:
   - Verify every listed `auth_methods` and `api_protocol` (e.g., Linear/Monday/Plain/Shopify are GraphQL or REST+GraphQL; WooCommerce/Twilio/DataForSEO support Basic Auth; Binance uses API Key + HMAC Signature).
   - Ensure `buildability_verdict` is strictly consistent with `access_model`: `Ready Today (Easy Win)` requires `Self-Serve Free / Trial` without major review/paywall blockers; `Self-Serve Paid Plan`, `Self-Serve Dev + App Review`, and `Admin / Customer Account Required` should normally be `Buildable with Friction`; `Partner / Sales-Gated` should be `Gated / Needs Outreach` (unless a self-serve OAuth MCP exists, in which case `Buildable with Friction` with clear notes).
7. LOGGING CHANGES: Only add entries to `changes_made` when a substantive field actually changed (`auth_methods`, `access_model`, `api_protocol`, `api_breadth`, `mcp_status`, `openapi_spec_available`, `webhooks_supported`, `buildability_verdict`, `evidence_urls`). Do NOT fabricate fake changes if Pass 1 was already correct!
"""

    response = generate_content_throttled(
        gemini_client,
        model=GEMINI_MODEL,
        contents=critic_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CriticVerdict,
            temperature=0.0,
        ),
    )
    verdict = CriticVerdict.model_validate_json(response.text)

    # Re-check health of any newly introduced URLs
    new_urls = list(verdict.evidence_urls)
    if verdict.mcp_evidence_url:
        new_urls.append(verdict.mcp_evidence_url)
    final_health = dict(url_health)
    for u in new_urls:
        if u and u not in final_health:
            final_health[u] = check_url_health(u)
    # Keep health dict scoped to the final URLs
    scoped_health = {u: final_health.get(u, "UNCHECKED") for u in dict.fromkeys(new_urls) if u}

    # Compute deterministic programmatic diff on core classification fields
    core_fields = [
        "auth_methods",
        "access_model",
        "api_protocol",
        "api_breadth",
        "mcp_status",
        "openapi_spec_available",
        "webhooks_supported",
        "buildability_verdict",
    ]
    verdict_dict = verdict.model_dump(mode="json")
    programmatic_diffs: list[dict[str, Any]] = []
    change_strings: list[str] = []

    reason_by_field = {c.field: c.reason for c in verdict.changes_made}

    for field in core_fields:
        old_v = record.get(field)
        new_v = verdict_dict.get(field)
        if old_v != new_v:
            reason = reason_by_field.get(field, "Corrected against live extracted docs / disconfirmation search.")
            programmatic_diffs.append({
                "id": record["id"],
                "name": name,
                "field": field,
                "old": old_v,
                "new": new_v,
                "reason": reason,
            })
            change_strings.append(f"{field}: {old_v} -> {new_v} ({reason})")

    if broken_urls:
        replaced = [u for u in broken_urls if u not in verdict.evidence_urls]
        if replaced:
            msg = f"Replaced {len(replaced)} broken/dead URL(s): {replaced}"
            programmatic_diffs.append({
                "id": record["id"],
                "name": name,
                "field": "evidence_urls",
                "old": broken_urls,
                "new": verdict.evidence_urls,
                "reason": msg,
            })
            change_strings.append(msg)

    updated = AppResearchRecord(
        id=record["id"],
        name=name,
        category=record["category"],
        hint=hint,
        one_liner=verdict.one_liner,
        auth_methods=verdict.auth_methods,
        auth_notes=verdict.auth_notes,
        access_model=verdict.access_model,
        access_notes=verdict.access_notes,
        api_protocol=verdict.api_protocol,
        api_breadth=verdict.api_breadth,
        api_surface_notes=verdict.api_surface_notes,
        mcp_status=verdict.mcp_status,
        mcp_evidence_url=verdict.mcp_evidence_url,
        openapi_spec_available=verdict.openapi_spec_available,
        webhooks_supported=verdict.webhooks_supported,
        buildability_verdict=verdict.buildability_verdict,
        primary_blocker=verdict.primary_blocker,
        evidence_urls=verdict.evidence_urls,
        confidence=verdict.confidence,
        composio_catalog_slugs=catalog_slugs,
        composio_coverage=cat_info.get("coverage", "Not in Catalog"),
        composio_tools_count=cat_info.get("total_tools_count", 0),
        composio_triggers_count=cat_info.get("total_triggers_count", 0),
        composio_auth_modes=cat_info.get("auth_modes", []),
        composio_managed_auth=bool(cat_info.get("composio_managed_auth_schemes")),
        composio_logo=cat_info.get("logo"),
        github_mcp_audit=github_audit,
        url_health=scoped_health,
        verification_changes=change_strings,
        human_audited=record.get("human_audited", False),
    )
    return updated, programmatic_diffs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Pass 2 Verification Loop")
    parser.add_argument("--input", type=str, default="data/pass1_results.json")
    parser.add_argument("--output", type=str, default="data/pass2_verified.json")
    parser.add_argument("--ids", type=str, default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    in_path = ROOT / args.input
    out_path = ROOT / args.output
    records = json.loads(in_path.read_text(encoding="utf-8"))

    deep_catalog_by_app: dict[str, dict[str, Any]] = {}
    if DEEP_CATALOG_PATH.exists():
        deep_catalog_by_app = json.loads(DEEP_CATALOG_PATH.read_text(encoding="utf-8")).get("by_app", {})
    elif CATALOG_PATH.exists():
        raw_matches = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("matches", {})
        for k, v in raw_matches.items():
            deep_catalog_by_app[k] = {"all_slugs": [x["slug"] for x in v if x.get("slug")]}

    if args.ids:
        target_ids = {int(x.strip()) for x in args.ids.split(",") if x.strip()}
        selected = [r for r in records if r["id"] in target_ids]
    elif args.all:
        selected = records
    else:
        raise SystemExit("Specify --ids or --all")

    existing: dict[int, dict] = {}
    if args.resume and out_path.exists():
        for item in json.loads(out_path.read_text(encoding="utf-8")):
            existing[item["id"]] = item

    all_diffs: list[dict] = []
    if args.resume and DIFF_REPORT_PATH.exists():
        prev_rep = json.loads(DIFF_REPORT_PATH.read_text(encoding="utf-8"))
        all_diffs = prev_rep.get("diffs", [])

    todo = [r for r in selected if r["id"] not in existing]
    print(f"Pass 2 Verifier | model={GEMINI_MODEL} | target={len(selected)} | remaining={len(todo)}", flush=True)

    exa = Exa()
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Initialize Upgrade 2: Composio live GitHub auditor (gracefully disabled if github not yet authorized)
    composio = Composio()
    gh_session = composio.create(user_id="product_ops_researcher", toolkits=["github"])
    github_auditor = ComposioGitHubAuditor(gh_session)
    print(
        f"Composio GitHub Auditor: {'ACTIVE (' + str(github_auditor.repo_tool_slug) + ')' if github_auditor.enabled else 'INACTIVE (connect github via src/connect_integrations.py)'}",
        flush=True,
    )

    def _worker(rec: dict) -> tuple[AppResearchRecord, list[dict]]:
        return verify_single_record(rec, exa, gemini_client, deep_catalog_by_app, github_auditor)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        future_map = {pool.submit(_worker, r): r for r in todo}
        done = 0
        for fut in concurrent.futures.as_completed(future_map):
            rec = future_map[fut]
            done += 1
            try:
                updated, diffs = fut.result()
                existing[updated.id] = updated.model_dump(mode="json")
                all_diffs.extend(diffs)
                tag = f"{len(diffs)} FIX(ES)" if diffs else "CONFIRMED"
                print(
                    f"[{done}/{len(todo)}] #{updated.id:03d} {updated.name:<26} | {tag:<11} | "
                    f"{updated.access_model:<27} | {updated.mcp_status:<18} | {updated.buildability_verdict}",
                    flush=True,
                )
            except Exception as e:
                print(f"[{done}/{len(todo)}] ERROR #{rec['id']:03d} {rec['name']}: {type(e).__name__}: {e}", flush=True)

            if done % 5 == 0 or done == len(todo):
                ordered = [existing[k] for k in sorted(existing)]
                out_path.write_text(json.dumps(ordered, indent=2), encoding="utf-8")
                # Summarize diffs by field
                by_field: dict[str, int] = {}
                apps_changed: set[int] = set()
                for d in all_diffs:
                    by_field[d["field"]] = by_field.get(d["field"], 0) + 1
                    apps_changed.add(d["id"])
                report = {
                    "total_audited": len(existing),
                    "apps_modified": len(apps_changed),
                    "apps_unchanged": len(existing) - len(apps_changed),
                    "total_field_corrections": len(all_diffs),
                    "corrections_by_field": by_field,
                    "diffs": all_diffs,
                }
                DIFF_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nPass 2 Verification Complete. Saved {len(existing)} verified records to {out_path}.")


if __name__ == "__main__":
    main()
