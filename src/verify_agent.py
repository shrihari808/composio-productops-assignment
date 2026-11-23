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
DIFF_REPORT_PATH = ROOT / "data" / "verification_diff_report.json"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")

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
    catalog_matches: dict[str, list[dict]],
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

    # 4. Composio live catalog check (also check for `_mcp` sibling!)
    matched_toolkits = catalog_matches.get(name, [])
    catalog_slugs = [t["slug"] for t in matched_toolkits if t.get("slug")]

    # 5. Gemini Critic Agent
    critic_prompt = f"""You are a rigorous AI Product Ops QA Auditor verifying a Pass 1 research record for `{name}` ({hint}).
Your job is to catch hallucinations, broken links, missed paywalls/app reviews, and wrong MCP classifications using ONLY the fresh primary-source evidence below.

PASS 1 RECORD TO AUDIT:
{json.dumps({k: v for k, v in record.items() if k not in ('url_health', 'verification_changes', 'human_audited')}, indent=2)}

LIVE URL HEALTH CHECK RESULTS:
{json.dumps(url_health, indent=2)}

EXA /CONTENTS EXTRACTION STATUSES:
{json.dumps(exa_statuses, indent=2)}

LIVE EXTRACTED DOC TEXT (FROM EXA /CONTENTS):
{live_text}

DISCONFIRMATION SEARCH RESULTS (GATING, PRICING, REVIEW, OFFICIAL MCP):
{disconfirm_text}

LIVE COMPOSIO CATALOG MATCH:
{catalog_slugs if catalog_slugs else "None"}

STRICT AUDITING CHECKLIST:
1. BROKEN URLS: ONLY remove a URL if it returned HTTP 404/410 OR failed both HTTP check AND Exa `/contents`. Do NOT delete valid English official docs just because a bot-shielded portal (e.g. Meta, LinkedIn, Cloudflare) returned 403/400/timeout to a raw HTTP check. NEVER prefer non-English localized URLs (like `?locale=zh_CN`) over English official docs.
2. ACCESS MODEL PRECISION (most common Pass 1 mistake!):
   - Does the doc say API access is only on Pro/Business/Enterprise paid plans? -> `Self-Serve Paid Plan` (NOT `Self-Serve Free / Trial`).
   - Does production access require App Review, Business Verification, Developer Token approval, or Marketplace review (e.g., Google Ads, Meta Ads, Threads, WhatsApp, LinkedIn Ads, Pinterest, Amazon SP-API, Shopify public apps)? -> `Self-Serve Dev + App Review`.
   - Does it require an existing paying customer admin account with no free dev sandbox (e.g., Gladly, Gorgias, Brex, Ramp, Pylon)? -> `Admin / Customer Account Required` or `Partner / Sales-Gated`.
   - Does it require contacting sales / enterprise partnership to get API access or docs (e.g., DealCloud, PitchBook, Salesforce Commerce Cloud, NotebookLM Enterprise)? -> `Partner / Sales-Gated`.
3. MCP STATUS PRECISION:
   - Mark `Official MCP` ONLY if the vendor itself publishes/documents an official MCP server (or Composio ships a Provider MCP `*_mcp` that connects to the vendor's official MCP). Always provide a working `mcp_evidence_url` when `mcp_status != "None Found"`.
   - If Pass 1 said `None Found` but fresh search proves an official MCP server exists (very common in 2025–2026 for GitHub, Linear, Notion, Stripe, Cloudflare, Supabase, Sentry, Atlassian/Jira, HubSpot, Intercom, Datadog, Plaid, Firecrawl, Apify, Otter AI, Devin, etc.), UPGRADE it to `Official MCP` and log the change!
   - Conversely, if Pass 1 cited a random third-party GitHub repo as `Official MCP`, DOWNGRADE it to `Community MCP Only`!
4. AUTH & PROTOCOL PRECISION: Verify every listed `auth_methods` and `api_protocol` (e.g., Linear/Monday/Plain/Shopify are GraphQL or REST+GraphQL; WooCommerce/Twilio/DataForSEO support Basic Auth; Binance uses API Key + HMAC Signature).
5. LOGGING CHANGES: Only add entries to `changes_made` when a substantive field actually changed (`auth_methods`, `access_model`, `api_protocol`, `api_breadth`, `mcp_status`, `openapi_spec_available`, `webhooks_supported`, `buildability_verdict`, `evidence_urls`). Do NOT fabricate fake changes if Pass 1 was already correct!
"""

    response = gemini_client.models.generate_content(
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
    catalog_matches = {}
    if CATALOG_PATH.exists():
        catalog_matches = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("matches", {})

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
    print(f"Pass 2 Verifier | model={GEMINI_MODEL} | target={len(selected)} | remaining={len(todo)}")

    exa = Exa()
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def _worker(rec: dict) -> tuple[AppResearchRecord, list[dict]]:
        return verify_single_record(rec, exa, gemini_client, catalog_matches)

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
