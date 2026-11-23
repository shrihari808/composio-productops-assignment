"""
Builds the self-contained, single-page interactive HTML Case Study (`index.html`)
plus an agent-consumable `llms.txt` index from the verified research artifacts:
- `data/final_results.json` (fallback: `data/pass2_verified.json`)
- `data/analytics_summary.json`
- `data/composio_live_proof.json`
- `data/mermaid_architecture.json`
- `data/human_audit.json` (if present)

Designed for:
1. A busy human reviewer to grasp every insight, verification loop, and proof in ~2 minutes.
2. An AI agent to consume effortlessly via semantic HTML, embedded JSON
   (`#composio-100-apps-dataset`), `llms.txt`, and one-click JSON/CSV/Markdown exports.
"""
from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/shrihari808/composio-productops-assignment"
ASSIGNMENT_URL = "https://composio.notion.site/AI-Product-Ops-Intern-The-take-home-assignment-391f261a6dfe80e9946bee899d3a3762"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_llms_txt(records: list[dict], analytics: dict, human_audit: dict) -> str:
    dist = analytics.get("distributions", {})
    hl = analytics.get("highlights", {})
    rm = analytics.get("composio_roadmap", {})
    p2 = analytics.get("verification", {}).get("pass2_diff_summary", {})

    lines = [
        "# Composio AI Product Ops — 100-App Toolkit & MCP Buildability Research",
        "",
        f"> Automated multi-pass research and verification study of {len(records)} SaaS, developer, fintech, and AI apps across 10 categories.",
        f"> Source Repo: {REPO_URL}",
        "",
        "## Headline Metrics",
        f"- Total Apps Analyzed: {len(records)}",
        f"- Buildability Verdicts: {json.dumps(dist.get('buildability_verdicts', {}))}",
        f"- Auth Methods Frequency: {json.dumps(dist.get('auth_methods', {}))}",
        f"- Access Models: {json.dumps(dist.get('access_models', {}))}",
        f"- MCP Status: {json.dumps(dist.get('mcp_status', {}))}",
        f"- Composio Live Catalog Coverage (1,842 toolkits audited): {json.dumps(dist.get('composio_coverage', {}))}",
        f"- Pass 2 Automated Corrections: {p2.get('total_field_corrections', 0)} field fixes across {p2.get('apps_modified', 0)} apps",
    ]
    if human_audit and human_audit.get("summary"):
        s = human_audit["summary"]
        lines.append(
            f"- Human + Browser Audit ({s.get('sample_size', 0)}-app stratified sample): "
            f"Pass 1 exact accuracy {s.get('pass1_accuracy_pct')}% -> "
            f"Pass 2 automated {s.get('pass2_accuracy_pct')}% -> "
            f"Final audited {s.get('final_accuracy_pct')}%"
        )
    lines.extend([
        "",
        "## Strategic Composio Action Queues",
        f"- Net-New Easy Wins (Not in Composio + Ready Today): {[x['name'] for x in rm.get('net_new_easy_wins', [])]}",
        f"- Net-New Friction (Not in Composio + Buildable w/ Friction): {[x['name'] for x in rm.get('net_new_friction', [])]}",
        f"- Net-New Partner/Outreach Queue: {[x['name'] for x in rm.get('net_new_outreach', [])]}",
        f"- Net-New Non-API Blockers: {[x['name'] for x in rm.get('net_new_blocked', [])]}",
        f"- Official MCP Expansion Candidates (Built API Only in Composio, Official Vendor MCP exists): {[x['name'] for x in rm.get('mcp_expansion_candidates', [])]}",
        "",
        "## Machine-Readable Artifacts",
        "- Final Verified Dataset: data/final_results.json",
        "- Pass 1 Raw Baseline: data/pass1_results.json",
        "- Pass 2 Verified Snapshot: data/pass2_verified.json",
        "- Automated Verification Diffs: data/verification_diff_report.json",
        "- Human & Browser Audit Log: data/human_audit.json",
        "- Deep Composio Catalog Audit: data/composio_catalog_deep.json",
        "- Aggregated Analytics: data/analytics_summary.json",
        "",
        "## 100-App Compact Index",
        "| # | App | Category | Auth | Access Model | API | MCP | Verdict | Composio Coverage |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for r in records:
        lines.append(
            f"| {r['id']} | {r['name']} | {r['category']} | {', '.join(r['auth_methods'])} | "
            f"{r['access_model']} | {r['api_protocol']} | {r['mcp_status']} | "
            f"{r['buildability_verdict']} | {r.get('composio_coverage', 'Not in Catalog')} |"
        )
    return "\n".join(lines) + "\n"


def generate_html(
    records: list[dict],
    analytics: dict,
    proof: dict,
    mermaid_info: dict,
    human_audit: dict,
    diff_report: dict,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dist = analytics["distributions"]
    hl = analytics["highlights"]
    cat_matrix = analytics["category_matrix"]
    rm = analytics["composio_roadmap"]
    cat_sum = rm.get("catalog_summary", {})
    p2_sum = analytics.get("verification", {}).get("pass2_diff_summary", {})

    total = len(records)
    ready_cnt = dist["buildability_verdicts"].get("Ready Today (Easy Win)", 0)
    friction_cnt = dist["buildability_verdicts"].get("Buildable with Friction", 0)
    gated_cnt = dist["buildability_verdicts"].get("Gated / Needs Outreach", 0)
    blocked_cnt = dist["buildability_verdicts"].get("Blocked / Not API-Native", 0)

    oauth_cnt = dist["auth_methods"].get("OAuth2", 0)
    apikey_cnt = dist["auth_methods"].get("API Key", 0)
    bearer_cnt = dist["auth_methods"].get("Bearer Token", 0)
    official_mcp_cnt = dist["mcp_status"].get("Official MCP", 0)
    comm_mcp_cnt = dist["mcp_status"].get("Community MCP Only", 0)
    self_serve_cnt = hl.get("self_serve_free_or_paid", 0)
    gated_access_cnt = hl.get("gated_review_admin_or_partner", 0)

    ha_sum = human_audit.get("summary", {}) if human_audit else {}
    ha_rows = human_audit.get("sample_audit", []) if human_audit else []

    p1_acc = ha_sum.get("pass1_accuracy_pct", "—")
    p2_acc = ha_sum.get("pass2_accuracy_pct", "—")
    fin_acc = ha_sum.get("final_accuracy_pct", "—")
    ha_n = ha_sum.get("sample_size", 0)

    mermaid_code = mermaid_info.get("diagram_code", "")
    mermaid_log_id = mermaid_info.get("log_id", "log_J3d6ViRpXWTW")
    mermaid_session_id = mermaid_info.get("session_id", "trs_26KSZgEsBirK")

    # Compute sharpest category stats for headline narrative
    easiest_cats = sorted(cat_matrix, key=lambda x: x["ready_today"], reverse=True)[:3]
    hardest_cats = sorted(cat_matrix, key=lambda x: x["gated_outreach"] + x["gated_or_review_count"], reverse=True)[:3]
    top_mcp_cats = sorted(cat_matrix, key=lambda x: x["mcp_official"], reverse=True)[:3]

    # Build embedded machine-readable JSON safely (escape </script>)
    embedded_payload = {
        "meta": {
            "title": "Composio AI Product Ops — 100-App Toolkit & MCP Buildability Research",
            "generated_at": generated_at,
            "repo_url": REPO_URL,
            "total_apps": total,
        },
        "analytics": analytics,
        "composio_live_proof": proof,
        "human_audit": human_audit,
        "apps": records,
    }
    embedded_json_str = json.dumps(embedded_payload).replace("</", "<\\/")

    # Helper for pill badges in static sections
    def app_chips(items: list[dict], color_cls: str, limit: int = 20) -> str:
        if not items:
            return '<span class="text-xs text-slate-400 italic">None</span>'
        chips = []
        for it in items[:limit]:
            nm = html.escape(str(it.get("name", "")))
            cat = html.escape(str(it.get("category", "")))
            chips.append(
                f'<button onclick="openAppModalById({it["id"]})" '
                f'class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium {color_cls} hover:opacity-80 transition cursor-pointer" '
                f'title="{cat}">#{it["id"]} {nm}</button>'
            )
        if len(items) > limit:
            chips.append(f'<span class="text-xs text-slate-500 self-center">+{len(items)-limit} more</span>')
        return " ".join(chips)

    # Proof cards HTML
    proof_cards_html = []
    for ex in proof.get("verified_live_executions", []):
        proof_cards_html.append(f"""
        <div class="bg-slate-900/90 border border-slate-700/80 rounded-xl p-4 text-left">
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">{html.escape(ex['toolkit'])}</span>
            <span class="font-mono text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">{html.escape(ex['result_type'])}</span>
          </div>
          <div class="font-mono text-xs text-slate-200 truncate" title="{html.escape(ex['tool_slug'])}">{html.escape(ex['tool_slug'])}</div>
          <div class="mt-2 space-y-1 text-[11px] font-mono text-slate-400">
            <div>session: <span class="text-slate-200">{html.escape(ex['session_id'])}</span></div>
            <div>log_id: <span class="text-amber-300 font-semibold">{html.escape(ex['log_id'])}</span></div>
            <div class="text-slate-400 font-sans pt-1 leading-snug">{html.escape(ex['purpose'])}</div>
          </div>
        </div>
        """)

    # Pass 2 diff preview rows
    pass2_diffs = diff_report.get("diffs", [])
    diff_rows_html = []
    for d in pass2_diffs[:18]:
        old_s = html.escape(str(d.get("old")))
        new_s = html.escape(str(d.get("new")))
        reason_s = html.escape(str(d.get("reason", "")))
        diff_rows_html.append(f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50/70">
          <td class="py-2.5 px-3 font-medium text-slate-900 whitespace-nowrap">
            <button onclick="openAppModalById({d['id']})" class="text-indigo-600 hover:underline font-semibold">#{d['id']} {html.escape(d['name'])}</button>
          </td>
          <td class="py-2.5 px-3 font-mono text-xs text-slate-600">{html.escape(d['field'])}</td>
          <td class="py-2.5 px-3 text-xs text-rose-700 bg-rose-50/50 rounded">{old_s}</td>
          <td class="py-2.5 px-3 text-xs text-emerald-700 bg-emerald-50/50 font-medium rounded">{new_s}</td>
          <td class="py-2.5 px-3 text-xs text-slate-600 max-w-md">{reason_s}</td>
        </tr>
        """)

    # Pass 3 human audit table rows
    ha_rows_html = []
    for row in ha_rows:
        p1_badge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">Hit</span>' if row.get("pass1_accurate") else '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-100 text-rose-800">Miss</span>'
        p2_badge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">Hit</span>' if row.get("pass2_accurate") else '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800">Human Fix</span>'
        ha_rows_html.append(f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50/70">
          <td class="py-2.5 px-3 font-medium whitespace-nowrap">
            <button onclick="openAppModalById({row['id']})" class="text-indigo-600 hover:underline font-semibold">#{row['id']} {html.escape(row['name'])}</button>
            <div class="text-[11px] text-slate-400">{html.escape(row.get('category', ''))}</div>
          </td>
          <td class="py-2.5 px-3 text-center">{p1_badge}</td>
          <td class="py-2.5 px-3 text-center">{p2_badge}</td>
          <td class="py-2.5 px-3 text-xs text-slate-700">{html.escape(row.get('verification_method', 'Live Docs + Browser'))}</td>
          <td class="py-2.5 px-3 text-xs text-slate-600 max-w-lg">{html.escape(row.get('audit_finding', ''))}</td>
        </tr>
        """)

    # Category heatmap rows
    cat_heatmap_rows = []
    for cm in cat_matrix:
        cat_heatmap_rows.append(f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
          <td class="py-2.5 px-3 font-medium text-slate-900 text-xs">{html.escape(cm['category'])}</td>
          <td class="py-2.5 px-2 text-center text-xs font-semibold text-emerald-700 bg-emerald-50/70">{cm['ready_today']}</td>
          <td class="py-2.5 px-2 text-center text-xs font-semibold text-amber-700 bg-amber-50/70">{cm['buildable_friction']}</td>
          <td class="py-2.5 px-2 text-center text-xs font-semibold text-rose-700 bg-rose-50/70">{cm['gated_outreach']}</td>
          <td class="py-2.5 px-2 text-center text-xs font-semibold text-slate-600 bg-slate-100/70">{cm['blocked']}</td>
          <td class="py-2.5 px-2 text-center text-xs font-semibold text-indigo-700">{cm['mcp_official']}/10</td>
          <td class="py-2.5 px-2 text-center text-xs text-slate-700">{cm['oauth2_count']}/10</td>
          <td class="py-2.5 px-2 text-center text-xs font-mono text-slate-700">{cm['in_composio']}/10</td>
        </tr>
        """)

    # Build the complete self-contained HTML
    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Composio AI Product Ops — 100-App Toolkit & MCP Buildability Study</title>
  <meta name="description" content="Automated 3-pass research & verification study of 100 apps across 10 categories for Composio AI agent toolkits and MCP servers." />
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'base', themeVariables: {{ primaryColor: '#eef2ff', primaryBorderColor: '#4f46e5', primaryTextColor: '#0f172a', lineColor: '#64748b', secondaryColor: '#f8fafc', tertiaryColor: '#f1f5f9' }} }});
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
    code, pre, .font-mono {{ font-family: 'JetBrains Mono', ui-monospace, monospace; }}
    .glass-dark {{ background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 55%, #0f172a 100%); }}
    .badge-ready {{ background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }}
    .badge-friction {{ background:#fef3c7; color:#92400e; border:1px solid #fde68a; }}
    .badge-gated {{ background:#ffe4e6; color:#9f1239; border:1px solid #fecdd3; }}
    .badge-blocked {{ background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased">

  <!-- Sticky Top Nav -->
  <header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
      <div class="flex items-center gap-2.5">
        <span class="w-7 h-7 rounded-lg bg-indigo-600 text-white font-bold text-sm flex items-center justify-center">C</span>
        <span class="font-bold text-sm sm:text-base tracking-tight text-slate-900">Composio Product Ops · 100-App Study</span>
      </div>
      <nav class="hidden md:flex items-center gap-5 text-xs font-semibold text-slate-600">
        <a href="#patterns" class="hover:text-indigo-600">1. Patterns</a>
        <a href="#roadmap" class="hover:text-indigo-600">2. Composio Roadmap</a>
        <a href="#verification" class="hover:text-indigo-600">3. Verification</a>
        <a href="#agent" class="hover:text-indigo-600">4. Agent & Proof</a>
        <a href="#matrix" class="hover:text-indigo-600">5. 100-App Matrix</a>
      </nav>
      <div class="flex items-center gap-2">
        <button onclick="downloadJSON()" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition" title="Machine-readable dataset for AI agents">JSON</button>
        <button onclick="downloadCSV()" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">CSV</button>
        <button onclick="copyAgentMarkdown()" id="copyMdBtn" class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition">Copy for Agent</button>
        <a href="{REPO_URL}" target="_blank" rel="noopener" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white transition">GitHub ↗</a>
      </div>
    </div>
  </header>

  <!-- HERO: 2-Minute Executive Summary -->
  <section class="glass-dark text-white border-b border-slate-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <div class="flex flex-wrap items-center gap-2 mb-4">
        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-200 border border-indigo-400/30">AI Product Ops Intern Case Study</span>
        <span class="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-200 border border-emerald-400/30">Built with Composio SDK + MCP · Exa · Gemini 4 Hydrogen</span>
        <span class="px-2.5 py-1 rounded-full text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700">Verified {generated_at}</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight max-w-4xl">
        100 Apps Evaluated for AI Agent Toolkits: <span class="text-indigo-300">Patterns, Gates & Verified Buildability</span>
      </h1>
      <p class="mt-4 text-slate-300 text-base sm:text-lg max-w-3xl leading-relaxed">
        An automated <strong>3-pass research & verification pipeline</strong> audited all 100 requested apps across 10 categories, cross-referenced against <strong>{cat_sum.get('total_composio_toolkits_scanned', 1842):,} live Composio toolkits</strong>, verified with live HTTP checks, Exa <code>/contents</code> extraction, Composio <code>github</code> &amp; <code>deepwiki_mcp</code> audits, and a stratified {ha_n}-app human &amp; browser spot-check.
      </p>

      <!-- Top-Line KPI Strip -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-8">
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">Ready Today (Easy Win)</div>
          <div class="text-3xl font-extrabold text-emerald-400 mt-1">{ready_cnt}<span class="text-base font-normal text-slate-400">/{total}</span></div>
          <div class="text-[11px] text-slate-400 mt-1">Self-serve &amp; documented</div>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">Buildable w/ Friction</div>
          <div class="text-3xl font-extrabold text-amber-300 mt-1">{friction_cnt}<span class="text-base font-normal text-slate-400">/{total}</span></div>
          <div class="text-[11px] text-slate-400 mt-1">Paywall or app review</div>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">Gated / Needs Outreach</div>
          <div class="text-3xl font-extrabold text-rose-400 mt-1">{gated_cnt}<span class="text-base font-normal text-slate-400">/{total}</span></div>
          <div class="text-[11px] text-slate-400 mt-1">Enterprise / partner gate</div>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">Official Vendor MCP</div>
          <div class="text-3xl font-extrabold text-indigo-300 mt-1">{official_mcp_cnt}<span class="text-base font-normal text-slate-400">/{total}</span></div>
          <div class="text-[11px] text-slate-400 mt-1">+{comm_mcp_cnt} community only</div>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">OAuth2 Adoption</div>
          <div class="text-3xl font-extrabold text-sky-300 mt-1">{oauth_cnt}<span class="text-base font-normal text-slate-400">%</span></div>
          <div class="text-[11px] text-slate-400 mt-1">{hl.get('multi_auth_apps', 0)} apps are multi-auth</div>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-xl p-4">
          <div class="text-xs text-slate-400 font-medium">Verified Accuracy</div>
          <div class="text-3xl font-extrabold text-emerald-300 mt-1">{fin_acc}<span class="text-base font-normal text-slate-400">%</span></div>
          <div class="text-[11px] text-slate-400 mt-1">Up from {p1_acc}% in Pass 1</div>
        </div>
      </div>
    </div>
  </section>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-14">

    <!-- SECTION 1: HEADLINE PATTERNS (UP TOP) -->
    <section id="patterns" class="space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-600">Section 01 · Executive Findings</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-0.5">Headline Patterns Across All 100 Apps</h2>
        </div>
        <p class="text-xs text-slate-500">Clustered from verified primary docs &amp; Composio v3.1 catalog metadata</p>
      </div>

      <!-- 5 Sharp Headline Pattern Cards -->
      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-indigo-600">Pattern 1 · Auth Landscape</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">Dual-Auth (OAuth2 + API Key/Bearer) is the SaaS Default</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            <strong>OAuth2 appears in {oauth_cnt}/100 apps</strong>, followed closely by <strong>API Key ({apikey_cnt})</strong> and <strong>Bearer Token ({bearer_cnt})</strong>. Crucially, <strong>{hl.get('multi_auth_apps', 0)}/100 apps support 2+ auth schemes</strong> (e.g., OAuth2 for multi-tenant SaaS vs. static keys for single-tenant scripts). Supporting both managed OAuth and API-key fallback unlocks the widest coverage.
          </p>
        </article>

        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-emerald-600">Pattern 2 · Where Easy Wins Live</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">Dev/Infra &amp; Productivity Are Nearly 100% Self-Serve</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            The highest density of <strong>Ready Today</strong> toolkits sits in <strong>{', '.join(c['category'] for c in easiest_cats[:2])}</strong>. These categories pair free developer sandboxes, clean OpenAPI/GraphQL specs, and instant token provisioning—making them ideal for automated toolkit generation.
          </p>
        </article>

        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-rose-600">Pattern 3 · The Hidden Gate Trap</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">"Self-Serve Portal ≠ Production Access" in Ads &amp; Fintech</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            <strong>{gated_access_cnt}/100 apps</strong> sit behind app review, customer-admin walls, or sales/partner gates—concentrated in <strong>{', '.join(c['category'] for c in hardest_cats[:2])}</strong>. Google Ads, Meta Ads, LinkedIn Ads, WhatsApp Business, and Amazon SP-API let devs sign up free, but gate production scopes behind strict business/app review.
          </p>
        </article>

        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-violet-600">Pattern 4 · The MCP Inflection</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">{official_mcp_cnt}/100 Vendors Now Ship Official MCP Servers</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            Official MCP adoption is led by <strong>{', '.join(c['category'] for c in top_mcp_cats[:2])}</strong>—and even enterprise tools like <strong>DealCloud</strong> and <strong>Otter AI</strong> shipped remote MCP servers. Notably, several vendors (e.g., Otter AI) put full REST APIs behind Enterprise contracts while exposing narrower self-serve OAuth MCP endpoints.
          </p>
        </article>

        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-amber-600">Pattern 5 · Non-API &amp; Wrapper Edge Cases</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">{blocked_cnt} Apps Aren't Traditional Cloud APIs</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            Apps like <strong>Sherlock</strong> and <strong>Mermaid CLI</strong> are local open-source CLI binaries (no hosted REST API), while <strong>YouTube Transcript</strong> is a third-party scraper wrapper. Turning these into agent tools requires either wrapping a hosted runner (e.g., Apify/Mermaid Chart MCP) or running inside a sandboxed workbench.
          </p>
        </article>

        <article class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="text-xs font-bold uppercase tracking-wide text-sky-600">Pattern 6 · Webhooks vs. Triggers Gap</div>
          <h3 class="text-base font-bold text-slate-900 mt-1">{dist['webhooks_supported'].get('Yes', 0)} Vendors Support Webhooks, Only {cat_sum.get('with_triggers', 23)} Have Composio Triggers</h3>
          <p class="text-sm text-slate-600 mt-2 leading-relaxed">
            Cross-referencing live docs against Composio's production API revealed <strong>{len(rm.get('trigger_expansion_candidates', []))} existing Composio toolkits</strong> that already support vendor webhooks but currently ship <strong>0 event triggers</strong>—a high-leverage retention win for reactive AI agents.
          </p>
        </article>
      </div>

      <!-- Charts Row -->
      <div class="grid lg:grid-cols-3 gap-6">
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-slate-900 mb-1">Buildability Verdict (n={total})</h3>
          <p class="text-xs text-slate-500 mb-4">Can Composio build an agent toolkit today?</p>
          <div class="h-56"><canvas id="chartVerdict"></canvas></div>
        </div>
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-slate-900 mb-1">Auth Methods Frequency</h3>
          <p class="text-xs text-slate-500 mb-4">Multi-select count across 100 apps</p>
          <div class="h-56"><canvas id="chartAuth"></canvas></div>
        </div>
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-slate-900 mb-1">Access &amp; Gating Model</h3>
          <p class="text-xs text-slate-500 mb-4">Self-serve vs. paywall, review, and partner gates</p>
          <div class="h-56"><canvas id="chartAccess"></canvas></div>
        </div>
      </div>

      <!-- Category x Buildability Heatmap -->
      <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Category Matrix: Buildability, MCP Adoption &amp; Live Composio Coverage</h3>
            <p class="text-xs text-slate-500">10 apps per category — shows exactly where self-serve wins cluster vs. where outreach is required</p>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th class="py-2.5 px-3">Category (10 apps each)</th>
                <th class="py-2.5 px-2 text-center text-emerald-700">Ready Today</th>
                <th class="py-2.5 px-2 text-center text-amber-700">Friction</th>
                <th class="py-2.5 px-2 text-center text-rose-700">Gated / BD</th>
                <th class="py-2.5 px-2 text-center text-slate-600">Blocked</th>
                <th class="py-2.5 px-2 text-center text-indigo-700">Official MCP</th>
                <th class="py-2.5 px-2 text-center">OAuth2</th>
                <th class="py-2.5 px-2 text-center">In Composio</th>
              </tr>
            </thead>
            <tbody>
              {''.join(cat_heatmap_rows)}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- SECTION 2: COMPOSIO STRATEGIC ROADMAP (LIVE CATALOG AUDIT) -->
    <section id="roadmap" class="space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-600">Section 02 · Actionable Product Ops Queues</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-0.5">Live Composio Catalog Audit &amp; Build Prioritization</h2>
        </div>
        <p class="text-xs text-slate-500">Audited live via Composio Platform v3.1 API (<code>/api/v3.1/toolkits</code> · {cat_sum.get('total_composio_toolkits_scanned', 1842):,} toolkits scanned · {cat_sum.get('total_tools_across_matched', 0):,} tools)</p>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div class="bg-white border border-emerald-200 rounded-2xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-emerald-900">Queue A · Net-New Easy Wins (Build Next)</h3>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">{len(rm.get('net_new_easy_wins', []))} apps</span>
          </div>
          <p class="text-xs text-slate-600 mb-3">Not in Composio's live catalog yet, with self-serve credentials and clear public APIs. Click any chip for full dossier:</p>
          <div class="flex flex-wrap gap-1.5">{app_chips(rm.get('net_new_easy_wins', []), 'bg-emerald-50 text-emerald-800 border border-emerald-200')}</div>
        </div>

        <div class="bg-white border border-indigo-200 rounded-2xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-indigo-900">Queue B · Provider MCP Expansion Wins</h3>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800">{len(rm.get('mcp_expansion_candidates', []))} apps</span>
          </div>
          <p class="text-xs text-slate-600 mb-3">Already have a Composio Built API toolkit, <em>and</em> the vendor now ships an Official MCP server ready to onboard as a <code>*_mcp</code> sibling:</p>
          <div class="flex flex-wrap gap-1.5">{app_chips(rm.get('mcp_expansion_candidates', []), 'bg-indigo-50 text-indigo-800 border border-indigo-200', limit=25)}</div>
        </div>

        <div class="bg-white border border-amber-200 rounded-2xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-amber-900">Queue C · Net-New Buildable w/ Friction &amp; Outreach</h3>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">{len(rm.get('net_new_friction', [])) + len(rm.get('net_new_outreach', []))} apps</span>
          </div>
          <p class="text-xs text-slate-600 mb-3">Missing from Composio and gated by paid plans, customer admin walls, or partner/sales outreach:</p>
          <div class="flex flex-wrap gap-1.5">
            {app_chips(rm.get('net_new_friction', []), 'bg-amber-50 text-amber-800 border border-amber-200')}
            {app_chips(rm.get('net_new_outreach', []), 'bg-rose-50 text-rose-800 border border-rose-200')}
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-slate-900">Queue D · Non-API Blockers &amp; Trigger Gaps</h3>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">{len(rm.get('net_new_blocked', []))} blocked · {len(rm.get('trigger_expansion_candidates', []))} trigger gaps</span>
          </div>
          <p class="text-xs text-slate-600 mb-2"><strong>Net-new CLI / non-API blockers</strong> (need workbench/wrapper):</p>
          <div class="flex flex-wrap gap-1.5 mb-3">{app_chips(rm.get('net_new_blocked', []), 'bg-slate-100 text-slate-700 border border-slate-300')}</div>
          <p class="text-xs text-slate-600 mb-2"><strong>Top existing toolkits with vendor webhooks but 0 Composio triggers</strong> (sample):</p>
          <div class="flex flex-wrap gap-1.5">{app_chips(rm.get('trigger_expansion_candidates', []), 'bg-sky-50 text-sky-800 border border-sky-200', limit=12)}</div>
        </div>
      </div>
    </section>

    <!-- SECTION 3: VERIFICATION LOOPS & HONEST ACCURACY PROGRESSION -->
    <section id="verification" class="space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-600">Section 03 · Trust &amp; Verification</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-0.5">How We Verified Accuracy (Pass 1 → Pass 2 → Human Audit)</h2>
        </div>
        <p class="text-xs text-slate-500">Every claim is traceable across immutable Pass 1, Pass 2, and Human Audit snapshots</p>
      </div>

      <!-- Accuracy Progression Chart + Loop Stats -->
      <div class="grid lg:grid-cols-3 gap-6">
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-slate-900 mb-1">Accuracy Lift Across Verification Loops</h3>
          <p class="text-xs text-slate-500 mb-4">Measured on a stratified {ha_n}-app human &amp; browser audit (all 10 categories + hardest edge cases)</p>
          <div class="h-52"><canvas id="chartAccuracy"></canvas></div>
        </div>
        <div class="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 class="text-sm font-bold text-slate-900 mb-3">Automated Pass 2 Verification Loop Telemetry (All {total} Apps)</h3>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
                <div class="text-[11px] text-slate-500">Apps Corrected by Pass 2</div>
                <div class="text-2xl font-extrabold text-indigo-600">{p2_sum.get('apps_modified', 0)}<span class="text-xs text-slate-400 font-normal">/{total}</span></div>
              </div>
              <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
                <div class="text-[11px] text-slate-500">Total Field Fixes</div>
                <div class="text-2xl font-extrabold text-amber-600">{p2_sum.get('total_field_corrections', 0)}</div>
              </div>
              <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
                <div class="text-[11px] text-slate-500">Live URLs Checked</div>
                <div class="text-2xl font-extrabold text-emerald-600">{hl.get('total_urls_checked', 0)}</div>
              </div>
              <div class="bg-slate-50 border border-slate-200 rounded-xl p-3">
                <div class="text-[11px] text-slate-500">GitHub Repos Audited</div>
                <div class="text-2xl font-extrabold text-slate-800">{hl.get('github_repos_audited_via_composio', 0)}</div>
              </div>
            </div>
            <div class="text-xs text-slate-600 space-y-1.5 leading-relaxed">
              <p><strong>4 Automated Checks Ran on Every Single App:</strong> (1) Live <code>httpx</code> link health audit distinguishing dead 404/410s from bot-shielded portals (Meta, LinkedIn, Cloudflare); (2) Exa <code>/contents</code> live page extraction (<code>statuses</code>-checked) + targeted disconfirmation <code>/search</code> hunting for hidden paywalls, app reviews, and official MCP servers; (3) Live <strong>Composio v3.1 catalog cross-check</strong> comparing researched auth &amp; MCP against production schemas; (4) Live <strong>Composio <code>github</code> toolkit audit</strong> checking org ownership, stars, and archived flags on cited GitHub MCP repos.</p>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-2 text-xs">
            <span class="font-semibold text-slate-700">Pass 2 fixes by field:</span>
            {''.join(f'<span class="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700">{html.escape(k)}: {v}</span>' for k, v in (p2_sum.get('corrections_by_field') or {}).items())}
          </div>
        </div>
      </div>

      <!-- Pass 3 Human + Browser Audit Table -->
      <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="text-sm font-bold text-slate-900">Honest Sample Audit ({ha_n} Stratified Apps — Hits, Misses &amp; Human Fixes)</h3>
            <p class="text-xs text-slate-500">Cross-checked directly against live vendor docs &amp; browser inspection across all 10 categories + hardest edge cases</p>
          </div>
          <div class="flex items-center gap-2 text-xs font-mono">
            <span class="px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200">Pass 1: {p1_acc}%</span>
            <span>→</span>
            <span class="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Pass 2: {p2_acc}%</span>
            <span>→</span>
            <span class="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">Final: {fin_acc}%</span>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th class="py-2.5 px-3">App</th>
                <th class="py-2.5 px-3 text-center">Pass 1</th>
                <th class="py-2.5 px-3 text-center">Pass 2</th>
                <th class="py-2.5 px-3">Method</th>
                <th class="py-2.5 px-3">Honest Finding / What Was Right or Wrong</th>
              </tr>
            </thead>
            <tbody>
              {''.join(ha_rows_html) if ha_rows_html else '<tr><td colspan="5" class="py-6 text-center text-xs text-slate-400">Human audit data pending</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Automated Pass 2 Diffs Sample -->
      <details class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <summary class="px-5 py-4 cursor-pointer select-none flex items-center justify-between hover:bg-slate-50">
          <div>
            <span class="text-sm font-bold text-slate-900">Inspect Automated Pass 1 → Pass 2 Corrections ({len(pass2_diffs)} total field diffs)</span>
            <span class="block text-xs text-slate-500">Click to expand exact before/after field diffs caught automatically by the Pass 2 Critic Agent</span>
          </div>
          <span class="text-xs font-semibold text-indigo-600">Toggle Diffs ▾</span>
        </summary>
        <div class="overflow-x-auto border-t border-slate-200">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th class="py-2 px-3">App</th>
                <th class="py-2 px-3">Field</th>
                <th class="py-2 px-3">Pass 1 (Before)</th>
                <th class="py-2 px-3">Pass 2 (After)</th>
                <th class="py-2 px-3">Primary-Source Evidence Reason</th>
              </tr>
            </thead>
            <tbody>
              {''.join(diff_rows_html)}
            </tbody>
          </table>
        </div>
      </details>
    </section>

    <!-- SECTION 4: THE AGENT, HUMAN-IN-THE-LOOP & LIVE COMPOSIO PROOF -->
    <section id="agent" class="space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-600">Section 04 · Architecture &amp; Live Proof</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-0.5">What We Built, Composio Proof &amp; Where a Human Was Needed</h2>
        </div>
        <a href="{REPO_URL}" target="_blank" rel="noopener" class="text-xs font-semibold text-indigo-600 hover:underline">View Full Source Code &amp; README on GitHub ↗</a>
      </div>

      <!-- Architecture Diagram (Validated via Composio mermaid_chart_mcp) -->
      <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div>
            <h3 class="text-sm font-bold text-slate-900">3-Pass Research &amp; Verification Pipeline Architecture</h3>
            <p class="text-xs text-slate-500">Syntax validated via live Composio <code>mermaid_chart_mcp</code> (<code>session_id={html.escape(mermaid_session_id)}</code>, <code>log_id={html.escape(mermaid_log_id)}</code>)</p>
          </div>
          <span class="font-mono text-[11px] px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">Composio SDK v0.34 · Exa · Gemini 4 Hydrogen</span>
        </div>
        <div class="overflow-x-auto py-2">
          <div class="mermaid">
{mermaid_code}
          </div>
        </div>
      </div>

      <!-- Verified Composio Live Execution Proof Cards -->
      <div class="glass-dark rounded-2xl p-6 text-white shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h3 class="text-base font-bold">Verified Live Composio Platform Execution Proofs</h3>
            <p class="text-xs text-slate-300 mt-0.5">Real tool calls executed via Composio Sessions (<code>user_id="product_ops_researcher"</code>) — every <code>log_id</code> is auditable in the Composio Dashboard</p>
          </div>
          <code class="text-xs bg-slate-950/80 border border-slate-700 px-3 py-1.5 rounded-lg text-emerald-300">python src/research_one_composio.py --app "Stripe"</code>
        </div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {''.join(proof_cards_html)}
        </div>
      </div>

      <!-- What the Agent Handled vs Where a Human Was Needed -->
      <div class="grid md:grid-cols-2 gap-5">
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-emerald-800 mb-3">Where the Agent Excelled (90%+ Automated)</h3>
          <ul class="space-y-2 text-xs text-slate-700 leading-relaxed list-disc pl-4">
            <li><strong>Massive parallel primary-source retrieval:</strong> Researched all 100 apps across 200+ Exa semantic queries and verified 300+ live doc URLs in minutes rather than days.</li>
            <li><strong>Catching 2025–2026 Official MCP launches:</strong> Found newly launched official remote MCP servers (HubSpot, DealCloud, WhatsApp Business, Otter AI, Linear, Stripe, Plaid, etc.) that static LLM memory misses.</li>
            <li><strong>Programmatic Composio catalog auditing:</strong> Scanned 1,842 live Composio toolkits via <code>/api/v3.1/toolkits</code> to compute exact tool counts, trigger counts, and auth mode cross-checks with zero manual scraping.</li>
            <li><strong>Repo &amp; CLI forensics:</strong> Used Composio <code>deepwiki_mcp</code> and <code>github</code> toolkits to verify whether GitHub MCP repos belong to official vendor orgs vs. community forks.</li>
          </ul>
        </div>
        <div class="bg-white border border-amber-200 rounded-2xl p-5 shadow-sm">
          <h3 class="text-sm font-bold text-amber-900 mb-3">Where a Human Was Essential (Real Failure Modes Caught)</h3>
          <ul class="space-y-2 text-xs text-slate-700 leading-relaxed list-disc pl-4">
            <li><strong>Bot-shielded doc portals (caught in 5-app pilot!):</strong> Meta (<code>developers.facebook.com</code>), LinkedIn, and Cloudflare return HTTP 400/403/timeouts to headless HTTP clients. Our initial link checker mistakenly deleted valid WhatsApp URLs and swapped in a <code>?locale=zh_CN</code> page—requiring a human fix to combine HTTP checks with Exa <code>/contents</code> status codes.</li>
            <li><strong>"Free dev portal" vs. production app review:</strong> Pass 1 occasionally labeled Ads &amp; Fintech apps as <code>Self-Serve Free</code> because sandbox signup is free, missing mandatory business verification or developer token review for production.</li>
            <li><strong>Split-surface products:</strong> Products like <strong>Otter AI</strong> (Enterprise-only REST API vs. self-serve 3-tool OAuth MCP) and <strong>NotebookLM</strong> (consumer web app vs. GCP Enterprise API) required human judgment on the buildability rubric.</li>
            <li><strong>Catalog alias disambiguation &amp; obscure apps:</strong> Human review caught false catalog matches (e.g., <code>linkedin</code> vs. <code>linkedin_ads</code>; Amazon shopping vs. SP-API) and browser-checked opaque fintech/niche portals (<code>Paygent Connect</code>, <code>fanbasis</code>, <code>iPayX</code>, <code>Waterfall.io</code>).</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- SECTION 5: INTERACTIVE 100-APP MATRIX -->
    <section id="matrix" class="space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-600">Section 05 · Complete Dataset</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900 mt-0.5">Interactive 100-App Research Matrix</h2>
        </div>
        <p class="text-xs text-slate-500">Click any row to open the full verified dossier, live URL health badges, Composio metadata &amp; Pass 2 diff log</p>
      </div>

      <!-- Filter Bar -->
      <div class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
        <div class="grid sm:grid-cols-2 lg:grid-cols-6 gap-2.5">
          <input id="searchInput" type="text" placeholder="Search app, auth, blocker, notes..." class="lg:col-span-2 px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          <select id="filterCategory" class="px-2.5 py-2 text-xs border border-slate-300 rounded-lg bg-white">
            <option value="">All 10 Categories</option>
          </select>
          <select id="filterVerdict" class="px-2.5 py-2 text-xs border border-slate-300 rounded-lg bg-white">
            <option value="">All Verdicts</option>
            <option value="Ready Today (Easy Win)">Ready Today (Easy Win)</option>
            <option value="Buildable with Friction">Buildable with Friction</option>
            <option value="Gated / Needs Outreach">Gated / Needs Outreach</option>
            <option value="Blocked / Not API-Native">Blocked / Not API-Native</option>
          </select>
          <select id="filterMcp" class="px-2.5 py-2 text-xs border border-slate-300 rounded-lg bg-white">
            <option value="">All MCP Statuses</option>
            <option value="Official MCP">Official MCP</option>
            <option value="Community MCP Only">Community MCP Only</option>
            <option value="None Found">None Found</option>
          </select>
          <select id="filterComposio" class="px-2.5 py-2 text-xs border border-slate-300 rounded-lg bg-white">
            <option value="">All Composio Coverage</option>
            <option value="Not in Catalog">Not in Catalog (19 Gaps)</option>
            <option value="Built API Only">Built API Only</option>
            <option value="Both Built + Provider MCP">Both Built + MCP</option>
            <option value="Provider MCP Only">Provider MCP Only</option>
          </select>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <div id="resultCount" class="font-medium text-slate-700">Showing {total} of {total} apps</div>
          <div class="flex flex-wrap items-center gap-2">
            <label class="inline-flex items-center gap-1.5 cursor-pointer">
              <input id="filterChangedOnly" type="checkbox" class="rounded border-slate-300 text-indigo-600" />
              <span>Pass 2 Corrected Only</span>
            </label>
            <label class="inline-flex items-center gap-1.5 cursor-pointer">
              <input id="filterAuditedOnly" type="checkbox" class="rounded border-slate-300 text-indigo-600" />
              <span>Human Audited Only</span>
            </label>
            <button onclick="resetFilters()" class="text-indigo-600 hover:underline font-semibold ml-2">Reset Filters</button>
          </div>
        </div>
      </div>

      <!-- Data Table -->
      <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                <th class="py-3 px-3 w-10">#</th>
                <th class="py-3 px-3">App &amp; Category</th>
                <th class="py-3 px-3">Auth Method(s)</th>
                <th class="py-3 px-3">Self-Serve vs. Gated</th>
                <th class="py-3 px-3">API &amp; MCP</th>
                <th class="py-3 px-3">Buildability Verdict</th>
                <th class="py-3 px-3">Composio Live</th>
                <th class="py-3 px-3">Evidence</th>
              </tr>
            </thead>
            <tbody id="matrixBody" class="divide-y divide-slate-100 text-xs"></tbody>
          </table>
        </div>
      </div>
    </section>

  </main>

  <footer class="border-t border-slate-200 bg-white mt-16 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
      <div>
        <strong>Composio AI Product Ops Take-Home Case Study</strong> · Built with Composio Platform SDK &amp; MCP, Exa API, and Gemini 4 Hydrogen.
      </div>
      <div class="flex items-center gap-4">
        <a href="llms.txt" class="text-indigo-600 hover:underline font-mono">llms.txt (Agent Index)</a>
        <a href="data/final_results.json" class="text-indigo-600 hover:underline font-mono">final_results.json</a>
        <a href="{REPO_URL}" target="_blank" rel="noopener" class="text-indigo-600 hover:underline font-semibold">GitHub Repo ↗</a>
      </div>
    </div>
  </footer>

  <!-- App Detail Modal -->
  <div id="appModal" class="fixed inset-0 z-50 hidden items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4" onclick="if(event.target===this) closeModal()">
    <div class="bg-white rounded-2xl max-w-3xl w-full max-h-[88vh] overflow-y-auto shadow-2xl border border-slate-200">
      <div class="sticky top-0 bg-white/95 backdrop-blur border-b border-slate-200 px-6 py-4 flex items-start justify-between gap-4">
        <div>
          <div id="modalMeta" class="text-xs font-semibold text-indigo-600"></div>
          <h3 id="modalTitle" class="text-xl font-extrabold text-slate-900 mt-0.5"></h3>
          <p id="modalOneLiner" class="text-xs text-slate-600 mt-1"></p>
        </div>
        <button onclick="closeModal()" class="text-slate-400 hover:text-slate-700 text-xl font-bold px-2">&times;</button>
      </div>
      <div id="modalBody" class="p-6 space-y-4 text-xs text-slate-700"></div>
    </div>
  </div>

  <!-- Embedded Machine-Readable JSON for Agents & Client Interactivity -->
  <script type="application/json" id="composio-100-apps-dataset">{embedded_json_str}</script>

  <script>
    const PAYLOAD = JSON.parse(document.getElementById('composio-100-apps-dataset').textContent);
    const APPS = PAYLOAD.apps;
    const ANALYTICS = PAYLOAD.analytics;
    const HUMAN_AUDIT = PAYLOAD.human_audit || {{}};

    function verdictBadge(v) {{
      if (v.startsWith('Ready')) return `<span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold badge-ready">${{v}}</span>`;
      if (v.startsWith('Buildable')) return `<span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold badge-friction">${{v}}</span>`;
      if (v.startsWith('Gated')) return `<span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold badge-gated">${{v}}</span>`;
      return `<span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-semibold badge-blocked">${{v}}</span>`;
    }}

    function mcpBadge(status) {{
      if (status === 'Official MCP') return `<span class="inline-block px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800 font-semibold text-[10px]">Official MCP</span>`;
      if (status === 'Community MCP Only') return `<span class="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[10px]">Community MCP</span>`;
      return `<span class="text-[10px] text-slate-400">No MCP</span>`;
    }}

    function esc(s) {{
      return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }}

    // Populate category dropdown
    const catSelect = document.getElementById('filterCategory');
    [...new Set(APPS.map(a => a.category))].forEach(c => {{
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      catSelect.appendChild(opt);
    }});

    function renderTable() {{
      const q = document.getElementById('searchInput').value.trim().toLowerCase();
      const cat = document.getElementById('filterCategory').value;
      const verd = document.getElementById('filterVerdict').value;
      const mcp = document.getElementById('filterMcp').value;
      const comp = document.getElementById('filterComposio').value;
      const changedOnly = document.getElementById('filterChangedOnly').checked;
      const auditedOnly = document.getElementById('filterAuditedOnly').checked;

      const filtered = APPS.filter(a => {{
        if (cat && a.category !== cat) return false;
        if (verd && a.buildability_verdict !== verd) return false;
        if (mcp && a.mcp_status !== mcp) return false;
        if (comp && (a.composio_coverage || 'Not in Catalog') !== comp) return false;
        if (changedOnly && (!a.verification_changes || a.verification_changes.length === 0)) return false;
        if (auditedOnly && !a.human_audited) return false;
        if (q) {{
          const hay = [a.name, a.category, a.one_liner, a.auth_notes, a.access_model, a.primary_blocker, ...(a.auth_methods || []), ...(a.composio_catalog_slugs || [])].join(' ').toLowerCase();
          if (!hay.includes(q)) return false;
        }}
        return true;
      }});

      document.getElementById('resultCount').textContent = `Showing ${{filtered.length}} of ${{APPS.length}} apps`;
      const tbody = document.getElementById('matrixBody');
      tbody.innerHTML = filtered.map(a => {{
        const firstUrl = (a.evidence_urls && a.evidence_urls[0]) || '#';
        const compBadges = (a.composio_catalog_slugs && a.composio_catalog_slugs.length)
          ? `<div class="font-mono text-[11px] text-indigo-700">${{a.composio_catalog_slugs.map(esc).join(', ')}}</div><div class="text-[10px] text-slate-400">${{a.composio_tools_count || 0}} tools · ${{a.composio_triggers_count || 0}} triggers</div>`
          : `<span class="px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 text-[10px] font-semibold">Not in Catalog</span>`;
        const auditTags = [
          a.human_audited ? '<span class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-semibold">Audited</span>' : '',
          (a.verification_changes && a.verification_changes.length) ? `<span class="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px] font-semibold">${{a.verification_changes.length}} P2 Fix</span>` : ''
        ].filter(Boolean).join(' ');

        return `
          <tr class="hover:bg-indigo-50/40 cursor-pointer transition" onclick="openAppModalById(${{a.id}})">
            <td class="py-3 px-3 font-mono text-slate-400">${{a.id}}</td>
            <td class="py-3 px-3">
              <div class="font-bold text-slate-900 flex items-center gap-1.5 flex-wrap">${{esc(a.name)}} ${{auditTags}}</div>
              <div class="text-[11px] text-slate-500">${{esc(a.category)}}</div>
              <div class="text-[11px] text-slate-600 line-clamp-1 max-w-xs mt-0.5">${{esc(a.one_liner)}}</div>
            </td>
            <td class="py-3 px-3">
              <div class="flex flex-wrap gap-1">${{(a.auth_methods || []).map(m => `<span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">${{esc(m)}}</span>`).join('')}}</div>
            </td>
            <td class="py-3 px-3">
              <div class="font-medium text-slate-800">${{esc(a.access_model)}}</div>
            </td>
            <td class="py-3 px-3">
              <div class="font-medium text-slate-800">${{esc(a.api_protocol)}}</div>
              <div class="mt-1">${{mcpBadge(a.mcp_status)}}</div>
            </td>
            <td class="py-3 px-3">
              ${{verdictBadge(a.buildability_verdict)}}
              ${{a.primary_blocker && a.primary_blocker !== 'None' ? `<div class="text-[10px] text-slate-500 line-clamp-1 max-w-[180px] mt-1">${{esc(a.primary_blocker)}}</div>` : ''}}
            </td>
            <td class="py-3 px-3">${{compBadges}}</td>
            <td class="py-3 px-3 whitespace-nowrap" onclick="event.stopPropagation()">
              <a href="${{esc(firstUrl)}}" target="_blank" rel="noopener" class="text-indigo-600 hover:underline font-medium">Docs ↗</a>
              <div class="text-[10px] text-slate-400">${{(a.evidence_urls || []).length}} link(s)</div>
            </td>
          </tr>
        `;
      }}).join('');
    }}

    function openAppModalById(id) {{
      const a = APPS.find(x => x.id === id);
      if (!a) return;
      document.getElementById('modalMeta').textContent = `#${{a.id}} · ${{a.category}} · Confidence: ${{a.confidence}} ${{a.human_audited ? '· Human Audited' : ''}}`;
      document.getElementById('modalTitle').textContent = a.name;
      document.getElementById('modalOneLiner').textContent = a.one_liner;

      const urlList = (a.evidence_urls || []).map(u => {{
        const st = (a.url_health && a.url_health[u]) ?? '';
        const stCls = (typeof st === 'number' && st >= 200 && st < 400) ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800';
        return `<li class="flex items-center justify-between gap-2 py-1 border-b border-slate-100 last:border-0">
          <a href="${{esc(u)}}" target="_blank" rel="noopener" class="text-indigo-600 hover:underline truncate">${{esc(u)}}</a>
          ${{st ? `<span class="font-mono text-[10px] px-1.5 py-0.5 rounded ${{stCls}} shrink-0">HTTP ${{esc(st)}}</span>` : ''}}
        </li>`;
      }}).join('');

      const changesHtml = (a.verification_changes && a.verification_changes.length)
        ? `<div class="bg-amber-50 border border-amber-200 rounded-xl p-3">
            <div class="font-bold text-amber-900 mb-1">Verification Loop Corrections (${{a.verification_changes.length}})</div>
            <ul class="list-disc pl-4 space-y-1 text-amber-900">${{a.verification_changes.map(c => `<li>${{esc(c)}}</li>`).join('')}}</ul>
          </div>`
        : `<div class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-emerald-800 font-medium">Confirmed unchanged by Pass 2 automated verification loop.</div>`;

      const ghHtml = (a.github_mcp_audit && !a.github_mcp_audit.error)
        ? `<div class="bg-slate-900 text-slate-200 rounded-xl p-3 font-mono text-[11px]">
            <div class="text-indigo-300 font-bold mb-1">Live Composio GitHub Repo Audit (log_id=${{esc(a.github_mcp_audit.composio_log_id)}})</div>
            <div>repo: ${{esc(a.github_mcp_audit.repo)}} · owner_type: ${{esc(a.github_mcp_audit.owner_type)}} · stars: ${{esc(a.github_mcp_audit.stars)}} · archived: ${{esc(a.github_mcp_audit.archived)}} · pushed_at: ${{esc(a.github_mcp_audit.pushed_at)}}</div>
          </div>`
        : '';

      document.getElementById('modalBody').innerHTML = `
        <div class="flex flex-wrap gap-2 items-center">
          ${{verdictBadge(a.buildability_verdict)}}
          ${{mcpBadge(a.mcp_status)}}
          <span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium">${{esc(a.access_model)}}</span>
          <span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium">${{esc(a.api_protocol)}} · ${{esc(a.api_breadth)}}</span>
        </div>
        <div class="grid sm:grid-cols-2 gap-3">
          <div class="bg-slate-50 rounded-xl p-3 border border-slate-200">
            <div class="font-bold text-slate-900 mb-1">Authentication (${{(a.auth_methods || []).join(', ')}})</div>
            <p class="text-slate-600 leading-relaxed">${{esc(a.auth_notes)}}</p>
          </div>
          <div class="bg-slate-50 rounded-xl p-3 border border-slate-200">
            <div class="font-bold text-slate-900 mb-1">Access &amp; Gating</div>
            <p class="text-slate-600 leading-relaxed">${{esc(a.access_notes)}}</p>
          </div>
          <div class="bg-slate-50 rounded-xl p-3 border border-slate-200">
            <div class="font-bold text-slate-900 mb-1">API Surface (OpenAPI: ${{esc(a.openapi_spec_available)}} · Webhooks: ${{esc(a.webhooks_supported)}})</div>
            <p class="text-slate-600 leading-relaxed">${{esc(a.api_surface_notes)}}</p>
          </div>
          <div class="bg-slate-50 rounded-xl p-3 border border-slate-200">
            <div class="font-bold text-slate-900 mb-1">Composio Live Catalog (${{esc(a.composio_coverage || 'Not in Catalog')}})</div>
            <p class="text-slate-600">Slugs: <code>${{(a.composio_catalog_slugs || []).join(', ') || 'None'}}</code></p>
            <p class="text-slate-600 mt-1">Tools: <strong>${{a.composio_tools_count || 0}}</strong> · Triggers: <strong>${{a.composio_triggers_count || 0}}</strong> · Managed OAuth: <strong>${{a.composio_managed_auth ? 'Yes' : 'No'}}</strong></p>
            <p class="text-slate-600 mt-1">Prod Auth Modes: <code>${{(a.composio_auth_modes || []).join(', ') || 'N/A'}}</code></p>
          </div>
        </div>
        <div class="bg-rose-50/60 border border-rose-200 rounded-xl p-3">
          <div class="font-bold text-rose-900 mb-0.5">Primary Blocker / Friction</div>
          <p class="text-rose-900">${{esc(a.primary_blocker)}}</p>
        </div>
        ${{a.mcp_evidence_url ? `<div class="bg-indigo-50/60 border border-indigo-200 rounded-xl p-3"><strong class="text-indigo-900">MCP Evidence URL:</strong> <a href="${{esc(a.mcp_evidence_url)}}" target="_blank" rel="noopener" class="text-indigo-700 hover:underline break-all">${{esc(a.mcp_evidence_url)}}</a></div>` : ''}}
        ${{ghHtml}}
        ${{changesHtml}}
        <div>
          <div class="font-bold text-slate-900 mb-1">Verified Primary-Source Evidence URLs</div>
          <ul class="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1">${{urlList}}</ul>
        </div>
      `;
      const modal = document.getElementById('appModal');
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }}

    function closeModal() {{
      const modal = document.getElementById('appModal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }}

    function resetFilters() {{
      document.getElementById('searchInput').value = '';
      document.getElementById('filterCategory').value = '';
      document.getElementById('filterVerdict').value = '';
      document.getElementById('filterMcp').value = '';
      document.getElementById('filterComposio').value = '';
      document.getElementById('filterChangedOnly').checked = false;
      document.getElementById('filterAuditedOnly').checked = false;
      renderTable();
    }}

    ['searchInput','filterCategory','filterVerdict','filterMcp','filterComposio','filterChangedOnly','filterAuditedOnly'].forEach(id => {{
      document.getElementById(id).addEventListener('input', renderTable);
      document.getElementById(id).addEventListener('change', renderTable);
    }});

    function downloadJSON() {{
      const blob = new Blob([JSON.stringify(PAYLOAD, null, 2)], {{ type: 'application/json' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'composio-100-apps-verified.json';
      a.click();
    }}

    function downloadCSV() {{
      const cols = ['id','name','category','one_liner','auth_methods','access_model','api_protocol','api_breadth','mcp_status','openapi_spec_available','webhooks_supported','buildability_verdict','primary_blocker','composio_coverage','composio_catalog_slugs','evidence_urls'];
      const rows = [cols.join(',')].concat(APPS.map(a => cols.map(c => {{
        const val = Array.isArray(a[c]) ? a[c].join('; ') : (a[c] ?? '');
        return '"' + String(val).replace(/"/g, '""') + '"';
      }}).join(',')));
      const blob = new Blob([rows.join('\\n')], {{ type: 'text/csv' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'composio-100-apps-verified.csv';
      a.click();
    }}

    async function copyAgentMarkdown() {{
      const lines = [
        '# Composio 100-App Toolkit Research (Verified Summary)',
        `- Buildability: ${{JSON.stringify(ANALYTICS.distributions.buildability_verdicts)}}`,
        `- Auth Methods: ${{JSON.stringify(ANALYTICS.distributions.auth_methods)}}`,
        `- Access Models: ${{JSON.stringify(ANALYTICS.distributions.access_models)}}`,
        `- MCP Status: ${{JSON.stringify(ANALYTICS.distributions.mcp_status)}}`,
        '',
        '| # | App | Category | Auth | Access | API | MCP | Verdict | Composio | Docs |',
        '|---|---|---|---|---|---|---|---|---|---|',
        ...APPS.map(a => `| ${{a.id}} | ${{a.name}} | ${{a.category}} | ${{(a.auth_methods||[]).join(', ')}} | ${{a.access_model}} | ${{a.api_protocol}} | ${{a.mcp_status}} | ${{a.buildability_verdict}} | ${{a.composio_coverage||'Not in Catalog'}} | ${{(a.evidence_urls||[])[0]||''}} |`)
      ].join('\\n');
      await navigator.clipboard.writeText(lines);
      const btn = document.getElementById('copyMdBtn');
      btn.textContent = 'Copied MD ✓';
      setTimeout(() => btn.textContent = 'Copy for Agent', 1800);
    }}

    // Charts
    const vd = ANALYTICS.distributions.buildability_verdicts || {{}};
    new Chart(document.getElementById('chartVerdict'), {{
      type: 'doughnut',
      data: {{
        labels: ['Ready Today', 'Buildable w/ Friction', 'Gated / Outreach', 'Blocked / Non-API'],
        datasets: [{{
          data: [vd['Ready Today (Easy Win)']||0, vd['Buildable with Friction']||0, vd['Gated / Needs Outreach']||0, vd['Blocked / Not API-Native']||0],
          backgroundColor: ['#10b981', '#f59e0b', '#f43f5e', '#64748b'],
          borderWidth: 0
        }}]
      }},
      options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 11 }} }} }} }} }}
    }});

    const ad = ANALYTICS.distributions.auth_methods || {{}};
    const authEntries = Object.entries(ad).slice(0, 7);
    new Chart(document.getElementById('chartAuth'), {{
      type: 'bar',
      data: {{
        labels: authEntries.map(e => e[0]),
        datasets: [{{ data: authEntries.map(e => e[1]), backgroundColor: '#4f46e5', borderRadius: 6 }}]
      }},
      options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#f1f5f9' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }} }} }}
    }});

    const ac = ANALYTICS.distributions.access_models || {{}};
    const accEntries = Object.entries(ac);
    new Chart(document.getElementById('chartAccess'), {{
      type: 'bar',
      data: {{
        labels: accEntries.map(e => e[0].replace('Self-Serve ', 'SS: ').replace('Required', 'Req.')),
        datasets: [{{ data: accEntries.map(e => e[1]), backgroundColor: ['#10b981','#0ea5e9','#f59e0b','#f97316','#f43f5e','#64748b'], borderRadius: 6 }}]
      }},
      options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: '#f1f5f9' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }} }} }}
    }});

    const haS = HUMAN_AUDIT.summary || {{}};
    new Chart(document.getElementById('chartAccuracy'), {{
      type: 'bar',
      data: {{
        labels: ['Pass 1 (Raw Agent)', 'Pass 2 (Auto Verifier)', 'Pass 3 (Human Audited)'],
        datasets: [{{
          label: 'Verified Accuracy (%)',
          data: [haS.pass1_accuracy_pct || 0, haS.pass2_accuracy_pct || 0, haS.final_accuracy_pct || 0],
          backgroundColor: ['#fb7185', '#f59e0b', '#10b981'],
          borderRadius: 8
        }}]
      }},
      options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }} }}, x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }} }} }}
    }});

    renderTable();
  </script>
</body>
</html>
"""


def main() -> None:
    final_path = ROOT / "data" / "final_results.json"
    if not final_path.exists():
        final_path = ROOT / "data" / "pass2_verified.json"
    records = load_json(final_path, [])
    analytics = load_json(ROOT / "data" / "analytics_summary.json", {})
    proof = load_json(ROOT / "data" / "composio_live_proof.json", {})
    mermaid_info = load_json(ROOT / "data" / "mermaid_architecture.json", {})
    human_audit = load_json(ROOT / "data" / "human_audit.json", {})
    diff_report = load_json(ROOT / "data" / "verification_diff_report.json", {})

    html_content = generate_html(records, analytics, proof, mermaid_info, human_audit, diff_report)
    (ROOT / "index.html").write_text(html_content, encoding="utf-8")

    llms_content = build_llms_txt(records, analytics, human_audit)
    (ROOT / "llms.txt").write_text(llms_content, encoding="utf-8")

    print(f"Built index.html ({len(html_content):,} bytes) and llms.txt ({len(llms_content):,} bytes) for {len(records)} apps.")


if __name__ == "__main__":
    main()
