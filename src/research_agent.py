"""
Pass 1 Research Agent — Automated 100-App Toolkit Feasibility Researcher.

Stack:
- Exa API (`exa-py`): semantic retrieval with `type="auto"`, `objective`, and
  `contents={"highlights": True}` (per `build-with-exa` skill guidelines).
- Composio Platform SDK (`composio`): session-scoped runtime tool discovery &
  execution (`deepwiki_mcp` for open-source/GitHub repo architecture) plus live
  Composio catalog cross-referencing.
- Google Gemini (`google-genai`, model `gemini-4-hydrogen`): structured JSON
  synthesis into our strict Pydantic rubric (`src/schema.py`).

Usage:
  python src/research_agent.py --ids 2,10,28,58,92   # Pilot run on 5 tricky apps
  python src/research_agent.py --all --concurrency 6 # Full 100-app Pass 1 run
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from exa_py import Exa
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from composio import Composio
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
APPS_PATH = ROOT / "data" / "apps.json"
CATALOG_PATH = ROOT / "data" / "composio_catalog_match.json"
PASS1_OUT = ROOT / "data" / "pass1_results.json"
PASS1_TRACE = ROOT / "data" / "pass1_traces.json"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")

# Known GitHub repos for open-source / CLI apps where Composio's deepwiki_mcp adds primary-source evidence
GITHUB_REPO_HINTS = {
    "Twenty": "twentyhq/twenty",
    "Sherlock": "sherlock-project/sherlock",
    "Mermaid CLI": "mermaid-js/mermaid-cli",
    "Firecrawl": "mendableai/firecrawl",
    "Supabase": "supabase/supabase",
}


class LLMAppAnalysis(BaseModel):
    one_liner: str = Field(description="What the app does in one crisp sentence.")
    auth_methods: list[AuthMethod] = Field(
        description="Primary authentication method(s) supported by the API."
    )
    auth_notes: str = Field(
        description="Concise nuance on auth (e.g., OAuth2 PKCE, Private App tokens, Basic over API key, service account)."
    )
    access_model: AccessModel = Field(
        description="Self-serve free/trial vs paid plan vs app review vs admin/customer account vs partner/sales-gated vs open-source/local."
    )
    access_notes: str = Field(
        description="Specific details on sandbox/trial, paid tier requirement, app review, or partner/sales gate."
    )
    api_protocol: ApiProtocol = Field(description="Primary public API protocol.")
    api_breadth: ApiBreadth = Field(description="How broad the documented public API surface is.")
    api_surface_notes: str = Field(
        description="Key API objects/endpoints, notable gaps, or rate-limit/sandbox details."
    )
    mcp_status: McpStatus = Field(
        description="Whether an official vendor MCP server, community MCP only, or none was found in evidence."
    )
    mcp_evidence_url: str | None = Field(
        default=None,
        description="Direct URL from evidence for official or community MCP, or null if none.",
    )
    openapi_spec_available: Literal["Yes", "No", "Unknown"] = Field(
        description="Whether an official OpenAPI/Swagger/GraphQL schema is published."
    )
    webhooks_supported: Literal["Yes", "No", "Unknown"] = Field(
        description="Whether webhooks or event triggers are documented."
    )
    buildability_verdict: BuildabilityVerdict = Field(
        description="Could Composio build and ship this as an agent toolkit today?"
    )
    primary_blocker: str = Field(
        description="Main blocker or friction point (or 'None' if Ready Today)."
    )
    evidence_urls: list[str] = Field(
        min_length=1,
        description="2 to 4 exact URLs taken verbatim from the retrieved Exa/Composio evidence backing your answers.",
    )
    confidence: ConfidenceLevel = Field(
        description="High if official docs clearly confirm auth, gating, and API surface; Medium if partial; Low if sparse or ambiguous."
    )


def format_exa_results(results: Any, max_items: int = 6) -> tuple[str, list[str]]:
    blocks: list[str] = []
    urls: list[str] = []
    for item in (getattr(results, "results", None) or [])[:max_items]:
        url = getattr(item, "url", "") or ""
        title = getattr(item, "title", "") or "(untitled)"
        highlights = getattr(item, "highlights", None) or []
        snippet = "\n".join(h.strip() for h in highlights[:3] if h and h.strip())
        if not snippet:
            snippet = "(no highlight text returned)"
        urls.append(url)
        blocks.append(f"TITLE: {title}\nURL: {url}\nHIGHLIGHTS:\n{snippet}")
    return "\n\n---\n\n".join(blocks), urls


def query_composio_deepwiki(session: Any, repo_name: str) -> dict[str, Any]:
    """Use Composio's live `deepwiki_mcp` toolkit to inspect a GitHub repository's structure."""
    try:
        res = session.execute(
            "DEEPWIKI_MCP_READ_WIKI_STRUCTURE",
            arguments={"repoName": repo_name},
        )
        dump = res.model_dump(mode="json")
        return {
            "tool_slug": "DEEPWIKI_MCP_READ_WIKI_STRUCTURE",
            "repo": repo_name,
            "result_type": res.result_type,
            "log_id": res.log_id,
            "content": str(dump.get("data", ""))[:2000],
        }
    except Exception as e:
        return {"tool_slug": "DEEPWIKI_MCP_READ_WIKI_STRUCTURE", "repo": repo_name, "error": str(e)}


def research_single_app(
    app: dict[str, Any],
    exa: Exa,
    gemini_client: genai.Client,
    composio_session: Any | None,
    catalog_matches: dict[str, list[dict]],
) -> tuple[AppResearchRecord, dict[str, Any]]:
    t0 = time.time()
    name = app["name"]
    hint = app["hint"]
    category = app["category"]

    # 1. Exa Search #1: Official API docs, auth, gating, protocol, webhooks, OpenAPI
    api_query = f"{name} ({hint}) official developer API documentation authentication OAuth API key access"
    api_objective = (
        f"Find official developer documentation for {name} ({hint}). "
        "Prioritize primary developer portals, authentication guides, pricing/plan gates, "
        "partner/approval requirements, REST or GraphQL API references, OpenAPI specs, and webhooks."
    )
    res_api = exa.search(
        api_query,
        type="auto",
        objective=api_objective,
        contents={"highlights": True},
    )
    api_text, api_urls = format_exa_results(res_api, max_items=6)

    # 2. Exa Search #2: Official or community MCP server + developer access / approval gating
    mcp_query = f"{name} MCP server model context protocol official documentation OR API partner approval"
    mcp_objective = (
        f"Check whether {name} has an official vendor-hosted or official open-source MCP server "
        "(Model Context Protocol), or notable community MCP servers, and check for API approval or partner gates."
    )
    res_mcp = exa.search(
        mcp_query,
        type="auto",
        objective=mcp_objective,
        contents={"highlights": True},
    )
    mcp_text, mcp_urls = format_exa_results(res_mcp, max_items=4)

    # 3. Optional Composio live tool call (deepwiki_mcp) for open-source / GitHub-hosted apps
    composio_evidence = None
    repo = GITHUB_REPO_HINTS.get(name)
    if not repo and "github.com/" in hint.lower():
        m = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", hint)
        if m:
            repo = m.group(1)
    if repo and composio_session is not None:
        composio_evidence = query_composio_deepwiki(composio_session, repo)

    # 4. Composio live catalog match (informational context, not overriding public docs)
    matched_toolkits = catalog_matches.get(name, [])
    catalog_slugs = [t["slug"] for t in matched_toolkits if t.get("slug")]

    # 5. Gemini structured synthesis strictly grounded in retrieved evidence
    prompt = f"""You are a senior AI Product Operations analyst at Composio evaluating whether `{name}` can be turned into an AI agent toolkit / MCP integration.

TARGET APP:
- Name: {name}
- Category: {category}
- Website / Hint: {hint}
- Existing Composio catalog toolkits found: {catalog_slugs if catalog_slugs else "None"}

EVIDENCE FROM EXA SEARCH 1 (API Docs, Auth, Access, Surface):
{api_text}

EVIDENCE FROM EXA SEARCH 2 (MCP Server & Access Gating):
{mcp_text}

{f"EVIDENCE FROM COMPOSIO DEEPWIKI_MCP ({repo}):\n{composio_evidence.get('content', '')}" if composio_evidence and composio_evidence.get("content") else ""}

CRITICAL RUBRIC RULES:
1. Ground EVERY claim strictly in the evidence above. Do NOT invent URLs — `evidence_urls` and `mcp_evidence_url` MUST be exact URLs from the evidence above.
2. Distinguish carefully between:
   - `Self-Serve Free / Trial`: Any developer can create an account/sandbox and generate working API credentials for free or via free trial without sales approval.
   - `Self-Serve Paid Plan`: API access is self-serve once on a paid plan (no sales gate, just paywall).
   - `Self-Serve Dev + App Review`: Developer can register self-serve, but production access / scopes / publishing require app review, business verification, or developer token approval (e.g., Meta Ads, WhatsApp Business, Google Ads, LinkedIn Ads, Amazon SP-API).
   - `Admin / Customer Account Required`: Requires an active customer/workspace admin account (no standalone free developer sandbox).
   - `Partner / Sales-Gated`: Requires contacting sales, enterprise contract, or partner approval to even get API credentials/docs (e.g., DealCloud, PitchBook, Salesforce Commerce Cloud).
   - `Open-Source / Local Tool`: CLI, local binary, or self-hosted open-source tool without a central SaaS credential gate.
3. For `mcp_status`: Only mark `Official MCP` if the vendor themselves publishes/maintains an MCP server (in official docs or vendor GitHub org). Third-party / community repos count as `Community MCP Only`. Note: Composio's own `_mcp` catalog entry alone does NOT count as official unless the vendor maintains it (though Composio Provider MCPs wrap official vendor MCP servers).
4. For `buildability_verdict`:
   - `Ready Today (Easy Win)`: Documented public API, self-serve auth/sandbox, no major review/sales blocker.
   - `Buildable with Friction`: Public API exists, but requires paid plan, app review, complex OAuth/enterprise setup, or narrow/quirky endpoints.
   - `Gated / Needs Outreach`: Partner/sales gate, enterprise-only API, or opaque/private docs requiring BD outreach.
   - `Blocked / Not API-Native`: No public web API (CLI-only, local library, or third-party unofficial scraper wrapper).
5. Be brutally honest with `confidence`: set `Low` or `Medium` whenever official docs were missing, thin, behind a login wall, or contradictory.
"""

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMAppAnalysis,
            temperature=0.1,
        ),
    )

    parsed = LLMAppAnalysis.model_validate_json(response.text)

    record = AppResearchRecord(
        id=app["id"],
        name=name,
        category=category,
        hint=hint,
        **parsed.model_dump(),
        composio_catalog_slugs=catalog_slugs,
    )

    elapsed = round(time.time() - t0, 2)
    trace = {
        "id": app["id"],
        "name": name,
        "elapsed_sec": elapsed,
        "exa_api_urls_count": len(api_urls),
        "exa_mcp_urls_count": len(mcp_urls),
        "composio_tool_call": {
            "tool_slug": composio_evidence.get("tool_slug"),
            "repo": composio_evidence.get("repo"),
            "log_id": composio_evidence.get("log_id"),
            "result_type": composio_evidence.get("result_type"),
        }
        if composio_evidence
        else None,
        "confidence": record.confidence,
        "buildability_verdict": record.buildability_verdict,
    }
    return record, trace


def load_existing(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["id"]: item for item in data}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Pass 1 Research Agent")
    parser.add_argument("--ids", type=str, default="", help="Comma-separated app IDs to run (e.g. 2,10,28,58,92)")
    parser.add_argument("--all", action="store_true", help="Run across all 100 apps")
    parser.add_argument("--resume", action="store_true", help="Skip app IDs already present in pass1_results.json")
    parser.add_argument("--concurrency", type=int, default=5, help="Parallel worker threads")
    parser.add_argument("--out", type=str, default=str(PASS1_OUT), help="Output JSON path")
    args = parser.parse_args()

    apps = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    catalog_matches = {}
    if CATALOG_PATH.exists():
        catalog_matches = json.loads(CATALOG_PATH.read_text(encoding="utf-8")).get("matches", {})

    if args.ids:
        target_ids = {int(x.strip()) for x in args.ids.split(",") if x.strip()}
        selected = [a for a in apps if a["id"] in target_ids]
    elif args.all:
        selected = apps
    else:
        raise SystemExit("Specify --ids 2,10,28,58,92 or --all")

    out_path = Path(args.out)
    existing_records = load_existing(out_path) if args.resume else {}
    existing_traces = load_existing(PASS1_TRACE) if args.resume else {}

    todo = [a for a in selected if a["id"] not in existing_records]
    print(f"Pass 1 Research Agent | model={GEMINI_MODEL} | target={len(selected)} | remaining={len(todo)}")

    exa = Exa()
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Create a single Composio session for live deepwiki_mcp lookups
    composio = Composio()
    composio_session = composio.create(user_id="product_ops_researcher", toolkits=["deepwiki_mcp"])
    print(f"Composio session initialized: {composio_session.session_id}")

    errors: list[dict] = []

    def _worker(app_item: dict) -> tuple[AppResearchRecord, dict]:
        return research_single_app(app_item, exa, gemini_client, composio_session, catalog_matches)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        future_map = {pool.submit(_worker, a): a for a in todo}
        done_count = 0
        for fut in concurrent.futures.as_completed(future_map):
            app_item = future_map[fut]
            done_count += 1
            try:
                rec, tr = fut.result()
                existing_records[rec.id] = rec.model_dump(mode="json")
                existing_traces[rec.id] = tr
                print(
                    f"[{done_count}/{len(todo)}] #{rec.id:03d} {rec.name:<26} | "
                    f"{rec.access_model:<28} | {rec.mcp_status:<18} | {rec.buildability_verdict} ({rec.confidence}) [{tr['elapsed_sec']}s]",
                    flush=True,
                )
            except Exception as e:
                print(f"[{done_count}/{len(todo)}] ERROR #{app_item['id']:03d} {app_item['name']}: {type(e).__name__}: {e}", flush=True)
                errors.append({"id": app_item["id"], "name": app_item["name"], "error": f"{type(e).__name__}: {e}"})

            # Checkpoint every 5 completions
            if done_count % 5 == 0 or done_count == len(todo):
                ordered = [existing_records[k] for k in sorted(existing_records)]
                out_path.write_text(json.dumps(ordered, indent=2), encoding="utf-8")
                ordered_tr = [existing_traces[k] for k in sorted(existing_traces)]
                PASS1_TRACE.write_text(json.dumps(ordered_tr, indent=2), encoding="utf-8")

    print(f"\nCompleted Pass 1 batch. Saved {len(existing_records)} records to {out_path}. Errors: {len(errors)}")
    if errors:
        print("Errors:", json.dumps(errors, indent=2))


if __name__ == "__main__":
    main()
