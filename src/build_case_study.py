"""
Builds the tasteskill 2.5.1 single-page Case Study (`index.html`) and
agent-consumable index (`llms.txt`) from the verified 100-app research artifacts.

Design system: Leonxlnx/taste-skill (`design-taste-frontend`, tasteskill 2.5.1)
- Kind: software (`data-type="software"`, `site-kind="software"`)
- Dealt palette: `swap-pastels` (cool putty #c3d7e5 / #d0e0eb, ink #141414, deep teal #0f5257; zero violet)
- Dealt type: `geist` (Geist + Geist Mono, display weight 500, tight negative tracking)
- Dealt hero: `split` (`data-enter` entrance)
- Dealt moments: `word-highlight` (#thesis) + `line-carries-colour` (#agent dark band)
- Dealt structure: `nav-centre`, `footer-dark`, `close-word`, `solid` buttons, `wordmark`, `sharp` radius
- Icons: local UI glyph SVGs (`assets/icons/ui-*.svg`), no third-party company logos
- Explorer: software `app-frame` split workspace (100-app list + inline dossier inspector, no popup modal)
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/shrihari808/composio-productops-assignment"
LIVE_URL = "https://composio-productops-assignment.vercel.app"

PROOF_ICON_MAP: dict[str, str] = {
    "exa": "ui-globe.svg",
    "deepwiki_mcp": "ui-layers.svg",
    "github": "ui-search.svg",
    "mermaid_chart_mcp": "ui-shield-check.svg",
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def clean_prose(text: str) -> str:
    """Keep rendered audit notes free of stray exclamation marks."""
    return str(text or "").replace("!", "")


def build_llms_txt(records: list[dict], analytics: dict, human_audit: dict) -> str:
    dist = analytics.get("distributions", {})
    rm = analytics.get("composio_roadmap", {})
    p2 = analytics.get("verification", {}).get("pass2_diff_summary", {})

    lines = [
        "# Composio AI Product Ops — 100-App Toolkit & MCP Buildability Research",
        "",
        f"> Automated 3-pass research and verification study of {len(records)} SaaS, developer, fintech, and AI apps across 10 categories.",
        f"> Live Case Study: {LIVE_URL}",
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
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y")
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
    gated_access_cnt = hl.get("gated_review_admin_or_partner", 0)
    webhooks_yes = dist["webhooks_supported"].get("Yes", 0)

    ha_sum = human_audit.get("summary", {}) if human_audit else {}
    ha_rows = human_audit.get("sample_audit", []) if human_audit else []

    p1_acc = int(round(ha_sum.get("pass1_accuracy_pct", 50)))
    p2_acc = int(round(ha_sum.get("pass2_accuracy_pct", 80)))
    fin_acc = int(round(ha_sum.get("final_accuracy_pct", 100)))
    ha_n = ha_sum.get("sample_size", 20)

    mermaid_code = mermaid_info.get("diagram_code", "")
    mermaid_log_id = mermaid_info.get("log_id", "log_J3d6ViRpXWTW")
    mermaid_session_id = mermaid_info.get("session_id", "trs_26KSZgEsBirK")

    easiest_cats = sorted(cat_matrix, key=lambda x: x["ready_today"], reverse=True)[:2]
    hardest_cats = sorted(cat_matrix, key=lambda x: x["gated_outreach"] + x["gated_or_review_count"], reverse=True)[:2]
    top_mcp_cats = sorted(cat_matrix, key=lambda x: x["mcp_official"], reverse=True)[:2]

    # Machine-readable payload embedded for agents & client-side app-frame explorer
    embedded_payload = {
        "meta": {
            "title": "Composio Product Ops — 100-App Toolkit Feasibility Research",
            "generated_at": generated_at,
            "repo_url": REPO_URL,
            "live_url": LIVE_URL,
            "total_apps": total,
        },
        "analytics": analytics,
        "composio_live_proof": proof,
        "human_audit": human_audit,
        "apps": records,
    }
    embedded_json_str = json.dumps(embedded_payload).replace("</", "<\\/")

    # Hero live audit preview rows (real verified records from our 100-app study)
    by_id = {r["id"]: r for r in records}
    hero_preview_ids = [2, 10, 60, 81, 84, 92]
    hero_preview_rows = []
    for hid in hero_preview_ids:
        rec = by_id[hid]
        tag_cls = (
            "tag--ready"
            if rec["buildability_verdict"].startswith("Ready")
            else "tag--friction"
            if rec["buildability_verdict"].startswith("Buildable")
            else "tag--gated"
        )
        short_verdict = (
            "Ready today"
            if rec["buildability_verdict"].startswith("Ready")
            else "Friction"
            if rec["buildability_verdict"].startswith("Buildable")
            else "Gated"
        )
        hero_preview_rows.append(
            f'<a href="#matrix" class="preview-row" onclick="selectAppAndJump({rec["id"]}); return false;">'
            f'<span class="preview-row__app"><span><strong>{html.escape(rec["name"])}</strong>'
            f'<small>{html.escape(rec["access_model"])}</small></span></span>'
            f'<span class="preview-row__meta"><span class="mono-pill preview-mcp">{html.escape(rec["mcp_status"])}</span>'
            f'<span class="tag {tag_cls}">{short_verdict}</span></span>'
            f"</a>"
        )

    # Roadmap clickable inline links with interactive Show all / Show fewer toggle (zero dead "+N more")
    def queue_links(items: list[dict], limit: int = 12, badge: str = "") -> str:
        if not items:
            return '<span class="muted">None</span>'
        out = []
        for idx, it in enumerate(items):
            nm = html.escape(str(it.get("name", "")))
            extra_cls = " q-link--extra" if idx >= limit else ""
            b_html = f'<span class="q-badge">{html.escape(badge)}</span>' if badge else ""
            out.append(
                f'<a href="#matrix" class="q-link{extra_cls}" onclick="selectAppAndJump({it["id"]}); return false;">'
                f'<span>#{it["id"]} {nm}</span>{b_html}</a>'
            )
        if len(items) > limit:
            rem = len(items) - limit
            out.append(
                f'<button type="button" class="link-btn q-toggle" data-more="Show all {len(items)} (+{rem})" '
                f'data-less="Show fewer" onclick="toggleQueue(this)">Show all {len(items)} (+{rem})</button>'
            )
        return "".join(out)

    # Category matrix ledger rows (all columns kept; horizontally scrollable on narrow phones)
    cat_rows_html = []
    for cm in cat_matrix:
        cat_rows_html.append(
            f"<tr>"
            f'<td class="td-strong">{html.escape(cm["category"])}</td>'
            f'<td class="td-num td-ready">{cm["ready_today"]}</td>'
            f'<td class="td-num td-friction">{cm["buildable_friction"]}</td>'
            f'<td class="td-num td-gated">{cm["gated_outreach"]}</td>'
            f'<td class="td-num">{cm["blocked"]}</td>'
            f'<td class="td-num td-accent">{cm["mcp_official"]}/10</td>'
            f'<td class="td-num">{cm["oauth2_count"]}/10</td>'
            f'<td class="td-num">{cm["in_composio"]}/10</td>'
            f"</tr>"
        )

    # All 20 stratified human audit rows — sorted with human-caught fixes & browser catches first, ZERO text truncation
    priority_audit_ids = [84, 60, 58, 2, 50, 28]
    ha_priority_rank = {aid: i for i, aid in enumerate(priority_audit_ids)}
    ordered_ha_rows = sorted(
        ha_rows,
        key=lambda r: (
            ha_priority_rank.get(r["id"], 999),
            0 if not r.get("pass2_accurate") else 1,
            0 if not r.get("pass1_accurate") else 1,
            r["id"],
        ),
    )

    ha_rows_html = []
    for idx, row in enumerate(ordered_ha_rows):
        p1_s = '<span class="tag tag--ready">Hit</span>' if row.get("pass1_accurate") else '<span class="tag tag--gated">Miss</span>'
        p2_s = '<span class="tag tag--ready">Hit</span>' if row.get("pass2_accurate") else '<span class="tag tag--friction">Human fix</span>'
        finding_full = clean_prose(row.get("audit_finding", ""))
        row_cls = ' class="audit-row--extra"' if idx >= 8 else ""
        ha_rows_html.append(
            f"<tr{row_cls}>"
            f'<td class="td-app"><a href="#matrix" class="link-btn" onclick="selectAppAndJump({row["id"]}); return false;">#{row["id"]} {html.escape(row["name"])}</a>'
            f'<span class="td-sub">{html.escape(row.get("category", ""))}</span></td>'
            f'<td class="td-num">{p1_s}</td>'
            f'<td class="td-num">{p2_s}</td>'
            f'<td class="td-method">{html.escape(row.get("verification_method", ""))}</td>'
            f'<td class="td-finding">{html.escape(finding_full)}</td>'
            f"</tr>"
        )

    # All 30 Pass 2 automated diffs — complete untruncated evidence text
    def format_diff_val(val: Any) -> str:
        if isinstance(val, list):
            return ", ".join(str(x) for x in val) if val else "None"
        return str(val)

    pass2_diffs = diff_report.get("diffs", [])
    diff_rows_html = []
    for idx, d in enumerate(pass2_diffs):
        reason_full = clean_prose(str(d.get("reason", "")))
        row_cls = ' class="diff-row--extra"' if idx >= 10 else ""
        diff_rows_html.append(
            f"<tr{row_cls}>"
            f'<td class="td-app"><a href="#matrix" class="link-btn" onclick="selectAppAndJump({d["id"]}); return false;">#{d["id"]} {html.escape(d["name"])}</a></td>'
            f'<td class="mono-cell">{html.escape(d["field"])}</td>'
            f'<td class="diff-old">{html.escape(format_diff_val(d.get("old")))}</td>'
            f'<td class="diff-new">{html.escape(format_diff_val(d.get("new")))}</td>'
            f'<td class="td-finding">{html.escape(reason_full)}</td>'
            f"</tr>"
        )

    # Pass 2 field correction summary pills
    fix_pills_html = "".join(
        f'<span class="mono-pill">{html.escape(k.replace("_", " "))}: {v}</span>'
        for k, v in (p2_sum.get("corrections_by_field") or {}).items()
    )

    # Live Composio proof columns inside dark band (open ruled columns with local icons — no repetitive boxed cards)
    proof_cols_html = []
    for ex in proof.get("verified_live_executions", []):
        ic_file = PROOF_ICON_MAP.get(ex["toolkit"], "ui-check.svg")
        ic_html = (
            f'<img class="ic ic-20 ic-inv" src="assets/icons/{ic_file}" alt="" aria-hidden="true" width="20" height="20" loading="lazy">'
            if (ROOT / "assets" / "icons" / ic_file).exists()
            else ""
        )
        proof_cols_html.append(
            f'<div class="proof-col">'
            f'<div class="proof-col__top">'
            f'<span class="proof-col__tk">{ic_html}<span class="mono-pill mono-pill--inv">{html.escape(ex["toolkit"])}</span></span>'
            f'<span class="proof-status">{html.escape(ex["result_type"])}</span>'
            f"</div>"
            f'<p class="proof-col__slug">{html.escape(ex["tool_slug"])}</p>'
            f'<dl class="proof-meta">'
            f'<div><dt>Session</dt><dd>{html.escape(ex["session_id"])}</dd></div>'
            f'<div><dt>Log ID</dt><dd class="proof-log">{html.escape(ex["log_id"])}</dd></div>'
            f"</dl>"
            f'<p class="proof-col__desc">{html.escape(clean_prose(ex["purpose"]))}</p>'
            f"</div>"
        )

    # Pulsing diagram JSON spec (tasteskill assets/diagrams/diagram.js)
    diagram_spec = {
        "layout": "lanes",
        "size": "band",
        "ground": "dots",
        "alt": "100 target apps pass through Composio and Gemini into Exa doc retrieval, Composio catalog and GitHub auditing, and stratified human browser verification.",
        "input": {"label": "100 target apps", "icon": "ui:layers", "sub": "10 categories"},
        "core": {"label": "Composio + Gemini", "icon": "ui:cpu"},
        "lanes": [
            {"label": "Docs retrieved", "icon": "ui:globe", "done": True, "sub": "432 live URLs"},
            {"label": "Catalog audited", "icon": "ui:search", "done": True, "sub": "1,842 toolkits"},
            {"label": "Sample verified", "icon": "ui:shield-check", "done": True, "sub": f"{p1_acc}% to {fin_acc}%"},
        ],
        "motion": {"cycle": 3.2},
    }
    diagram_spec_json = json.dumps(diagram_spec).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en" data-type="software" data-radius="sharp" data-ground="sage" data-buttons="solid" data-motion>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Composio Ops: 100-app toolkit feasibility research</title>
<meta name="description" content="Automated three-pass audit of 100 SaaS, developer, fintech and AI apps for auth, gating, official MCP servers and live Composio catalog gaps.">
<meta property="og:type" content="website">
<meta property="og:title" content="Composio Ops: 100-app toolkit feasibility research">
<meta property="og:description" content="50 apps ready today, 89 official MCP servers, 1,842 live Composio toolkits audited, verified from 50% Pass 1 accuracy to 100% on a 20-app stratified sample.">
<meta property="og:image" content="{LIVE_URL}/share.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#c3d7e5">
<link rel="canonical" href="{LIVE_URL}/">
<meta name="site-kind" content="software">
<meta name="page-type" content="software">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400..700&family=Geist+Mono:wght@400..500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/system.css">
<link rel="stylesheet" href="assets/ui/cards.css">
<link rel="stylesheet" href="assets/motion/motion.css">
<link rel="stylesheet" href="assets/backgrounds/backgrounds.css">
<link rel="stylesheet" href="assets/layout/layout.css">
<link rel="stylesheet" href="assets/icons/icon.css">
<link rel="stylesheet" href="assets/diagrams/diagram.css">
<link rel="stylesheet" href="assets/moments/word-highlight/moment.css">
<link rel="stylesheet" href="assets/moments/line-carries-colour/moment.css">

<!-- Dealt palette & type tokens verbatim from start.mjs css (swap-pastels + geist + sharp) -->
<style>
:root {{
  --p-bg: #c3d7e5; --p-surface: #d0e0eb; --p-ink: #141414; --p-muted: #4a5068;
  --p-accent: #0f5257; --p-accent-ink: #ffffff; --p-action: #0f5257; --p-action-ink: #ffffff;
  --p-inv-bg: #141414; --p-inv-surface: #1e1f20; --p-inv-ink: #c3d7e5; --p-inv-muted: #808b94;
  --p-inv-accent: #c3d7e5; --p-inv-accent-ink: #141414; --p-inv-action: #c3d7e5; --p-inv-action-ink: #141414;
  --font-display: "Geist", system-ui, sans-serif;
  --font-text: "Geist", system-ui, sans-serif;
  --font-mono: "Geist Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --display-weight: 500;
  --display-tracking: -0.035em;
  --display-tracking-xl: -0.045em;
}}
</style>

<script>document.documentElement.classList.add('m-enter');setTimeout(()=>document.documentElement.classList.add('m-enter-done'),700)</script>
<script src="assets/backgrounds/backgrounds.js"></script>
<script>document.documentElement.classList.add('mo-js');setTimeout(()=>document.documentElement.classList.add('mo-safe'),2500)</script>
<link rel="modulepreload" href="assets/moments/moments.js">
<link rel="modulepreload" href="assets/moments/lib.js">
<link rel="modulepreload" href="assets/moments/word-highlight/moment.js">
<link rel="modulepreload" href="assets/moments/line-carries-colour/moment.js">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>

<!-- Scoped visual & data-workspace CSS obeying tasteskill spacing, single h3 scale, 7:1 body contrast, and zero-violet tokens -->
<style>
  /* Override rigid 100svh/200svh section locking from system.css so content NEVER clips, crushes, or bleeds across sections at any viewport height */
  html {{ scroll-behavior: smooth; }}
  main > :is(section, .section),
  footer.closing {{
    height: auto !important;
    min-height: 0 !important;
  }}
  main > :is(section, .section) {{
    padding: var(--s-9) 0 var(--s-8) !important;
    scroll-margin-top: var(--nav);
  }}
  main > .hero {{
    min-height: min(100svh, 860px) !important;
    padding: calc(var(--nav) + var(--hgap)) 0 var(--s-8) !important;
    display: flex;
    align-items: center;
  }}
  #thesis.statement {{
    min-height: 52svh !important;
    padding: var(--s-9) 0 !important;
    display: flex;
    align-items: center;
  }}
  main > :is(section, .section) > :is(.wrap, .container),
  footer.closing > .wrap {{
    height: auto !important;
  }}
  main > :is(section, .section).g2 > :is(.wrap, .container) {{
    display: flex !important;
    flex-direction: column;
    gap: var(--s-8) !important;
  }}
  main > :is(section, .section).g2 > :is(.wrap, .container) > .group {{
    flex: none !important;
  }}
  main > :is(section, .section) > .wrap > .fill {{
    flex: none !important;
  }}
  footer.closing {{
    padding: var(--s-9) 0 var(--s-7) !important;
  }}
  footer.closing .closing__cta {{
    margin-bottom: var(--s-8);
  }}
  main > .section .section-head {{
    margin-bottom: var(--s-6);
  }}

  /* Uniform h3 scale across all main sections */
  main h3 {{
    font-family: var(--font-text);
    font-size: var(--t-card);
    line-height: 1.3;
    font-weight: 500;
    letter-spacing: -0.012em;
  }}

  /* Hero live audit window inside .hero__media */
  .hero__media.audit-window {{
    background: var(--surface);
    border: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    padding: 0;
  }}
  .audit-window__bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-2);
    padding: var(--s-3) var(--s-5);
    border-bottom: 1px solid var(--line);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    color: var(--muted);
  }}
  .audit-window__list {{
    display: flex;
    flex-direction: column;
    padding: var(--s-2) var(--s-5);
    flex: 1 1 auto;
    min-height: 0;
  }}
  .preview-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
    padding: var(--s-3) 0;
    border-bottom: 1px solid var(--line);
    width: 100%;
    min-height: 44px;
    transition: background var(--m-in, 150ms) var(--ease);
  }}
  .preview-row:last-child {{ border-bottom: 0; }}
  .preview-row:hover {{ background: color-mix(in srgb, var(--ink) 4%, transparent); }}
  .preview-row:focus-visible {{ outline: 2px solid var(--action); outline-offset: 2px; }}
  .preview-row__app {{
    display: flex;
    align-items: center;
    gap: var(--s-3);
    min-width: 0;
  }}
  .preview-row__app strong {{
    display: block;
    font-weight: 500;
    font-size: var(--t-body);
    color: var(--ink);
    line-height: 1.3;
  }}
  .preview-row__app small {{
    display: block;
    font-size: var(--t-label);
    color: var(--muted);
  }}
  .preview-row__meta {{
    display: flex;
    align-items: center;
    gap: var(--s-2);
    flex-shrink: 0;
  }}
  /* Docked verification callout inside audit window (zero overlap at all viewports) */
  .audit-window .ly-float {{
    position: static;
    width: auto;
    margin: auto var(--s-5) var(--s-4);
    flex-shrink: 0;
  }}

  /* Tags & monospace pills (all >= 13px, zero violet, high contrast) */
  .tag {{
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: var(--r-sm);
    font-size: var(--t-label);
    font-weight: 500;
    line-height: 1.3;
    white-space: nowrap;
  }}
  .tag--ready {{ background: color-mix(in srgb, #0f5257 16%, var(--bg)); color: #0b3d41; border: 1px solid color-mix(in srgb, #0f5257 35%, transparent); }}
  .tag--friction {{ background: color-mix(in srgb, #8c6218 16%, var(--bg)); color: #5c3f0b; border: 1px solid color-mix(in srgb, #8c6218 35%, transparent); }}
  .tag--gated {{ background: color-mix(in srgb, #8f2d2d 15%, var(--bg)); color: #6e1c1c; border: 1px solid color-mix(in srgb, #8f2d2d 35%, transparent); }}
  .tag--blocked {{ background: color-mix(in srgb, var(--ink) 10%, var(--bg)); color: var(--ink); border: 1px solid var(--line); }}

  .mono-pill {{
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: var(--r-sm);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    color: var(--ink);
    background: color-mix(in srgb, var(--ink) 7%, transparent);
    white-space: nowrap;
  }}
  .mono-pill--inv {{
    color: var(--p-inv-ink);
    background: color-mix(in srgb, var(--p-inv-ink) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--p-inv-ink) 22%, transparent);
  }}
  .ic-inv {{ filter: invert(1) brightness(1.08); }}

  /* Hero compact 6-metric grid (always visible, never hidden on tablet/mobile) */
  .hero-facts {{
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--s-4) var(--s-5);
    margin-top: var(--s-6);
    padding-top: var(--s-5);
    border-top: 1px solid var(--line);
  }}
  .hero-facts dt {{ font-size: var(--t-label); color: var(--muted); font-weight: 500; }}
  .hero-facts dd {{ margin: 4px 0 0; font-size: var(--t-h3); font-weight: 500; letter-spacing: -0.02em; color: var(--ink); font-variant-numeric: tabular-nums; }}
  .hero-facts dd small {{ font-size: var(--t-label); font-weight: 400; color: var(--muted); display: block; margin-top: 2px; letter-spacing: 0; }}

  /* Pattern ledger cards (open ruled items with clear numeric anchors) */
  .finding-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--s-5) var(--gutter);
    margin-top: var(--s-4);
  }}
  .finding {{
    border-top: 1px solid var(--line);
    padding-top: var(--s-4);
  }}
  .finding__top {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--s-2);
    margin-bottom: var(--s-2);
  }}
  .finding__k {{ font-size: var(--t-label); font-weight: 500; color: var(--accent); margin: 0; }}
  .finding__n {{ font-family: var(--font-mono); font-size: var(--t-label); color: var(--muted); }}
  .finding h3 {{ margin: 0 0 var(--s-2); color: var(--ink); }}
  .finding p {{ font-size: var(--t-small); line-height: 1.55; margin: 0; color: var(--ink); }}

  /* Chart boxes (explicit stable heights so Chart.js never drops categorical axis labels) */
  .chart-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--gutter);
  }}
  .chart-box {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    padding: var(--s-5);
    display: flex;
    flex-direction: column;
    min-width: 0;
  }}
  .chart-box h3 {{ margin: 0 0 4px; color: var(--ink); }}
  .chart-box p {{ font-size: var(--t-small); color: var(--muted); margin: 0 0 var(--s-3); }}
  .chart-canvas {{ position: relative; height: 260px; width: 100%; }}
  .chart-canvas--catalog {{ height: 280px; }}
  .chart-canvas--catbar {{ height: 220px; }}
  .chart-canvas--acc {{ height: 280px; }}
  .chart-canvas--fixes {{ height: 250px; }}
  .roadmap-cat-chart {{ margin-bottom: var(--s-5); background: var(--surface); border: 1px solid var(--line); padding: var(--s-5); border-radius: var(--r-md); }}

  /* Roadmap asymmetric layout: chart left (span-6) + open ruled single-column queues right (span-6) */
  .roadmap-split {{
    align-items: start;
    row-gap: var(--s-5);
  }}
  .queue-list {{
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--s-4);
  }}
  .queue-row {{
    border-top: 1px solid var(--line);
    padding-top: var(--s-3);
    min-width: 0;
  }}
  .queue-row__head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--s-2);
    margin-bottom: 6px;
  }}
  .queue-row__head h3 {{ margin: 0; color: var(--ink); }}
  .queue-row p {{ font-size: var(--t-small); color: var(--ink); margin: 0 0 var(--s-2); line-height: 1.45; }}
  .queue-sublabel {{ font-size: var(--t-label); font-weight: 500; color: var(--muted); margin: var(--s-3) 0 6px !important; }}
  .q-links {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    align-items: center;
  }}
  .q-link {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--action);
    font-size: var(--t-small);
    font-weight: 500;
    line-height: 1.35;
    border-bottom: 1px solid transparent;
    transition: border-color var(--m-in, 150ms) var(--ease);
  }}
  .q-link:hover {{ border-bottom-color: var(--action); }}
  .q-link--extra {{ display: none; }}
  .q-links.is-expanded .q-link--extra {{ display: inline-flex; }}
  .q-badge {{
    font-family: var(--font-mono);
    font-size: 11px;
    color: #6e1c1c;
    background: color-mix(in srgb, #8f2d2d 13%, var(--bg));
    padding: 1px 5px;
    border-radius: var(--r-sm);
  }}
  .q-toggle {{ font-size: var(--t-label); font-family: var(--font-mono); color: var(--muted); }}
  .q-toggle:hover {{ color: var(--action); }}

  /* Data tables (clean 1px hairline ledger on section's own ground — horizontal scroll on narrow screens instead of hiding columns) */
  .ledger-wrap {{
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }}
  .ledger {{
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: var(--t-small);
  }}
  .ledger th {{
    font-size: var(--t-label);
    font-weight: 500;
    color: var(--muted);
    padding: var(--s-2) var(--s-3);
    border-bottom: 1px solid var(--line-strong);
    white-space: nowrap;
  }}
  .ledger th:first-child, .ledger td:first-child {{ padding-left: 0; }}
  .ledger th:last-child, .ledger td:last-child {{ padding-right: 0; }}
  .ledger td {{
    padding: 11px var(--s-3);
    border-bottom: 1px solid var(--line);
    color: var(--ink);
    vertical-align: top;
    line-height: 1.48;
  }}
  .ledger tr:last-child td {{ border-bottom: 0; }}
  .td-app {{ white-space: nowrap; min-width: 160px; }}
  .td-finding {{ min-width: 280px; max-width: 560px; overflow-wrap: break-word; }}
  .td-strong {{ font-weight: 500; }}
  .td-num {{ text-align: right; font-family: var(--font-mono); white-space: nowrap; }}
  .td-ready {{ color: #0f5257; font-weight: 500; }}
  .td-friction {{ color: #7a520f; font-weight: 500; }}
  .td-gated {{ color: #8f2d2d; font-weight: 500; }}
  .td-accent {{ color: var(--accent); font-weight: 500; }}
  .td-sub {{ display: block; font-size: var(--t-label); color: var(--muted); }}
  .td-method {{ font-size: var(--t-label); color: var(--muted); min-width: 170px; }}
  .mono-cell {{ font-family: var(--font-mono); font-size: var(--t-label); white-space: nowrap; }}
  .diff-old {{ color: #7d2222; min-width: 120px; max-width: 230px; overflow-wrap: anywhere; word-break: break-word; }}
  .diff-new {{ color: #0f5257; font-weight: 500; min-width: 120px; max-width: 230px; overflow-wrap: anywhere; word-break: break-word; }}
  .audit-row--extra, .diff-row--extra {{ display: none; }}
  .ledger-wrap.is-expanded .audit-row--extra,
  .ledger-wrap.is-expanded .diff-row--extra {{ display: table-row; }}
  .fix-pills {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: var(--s-3); }}
  .link-btn {{
    color: var(--action);
    font-weight: 500;
    border-bottom: 1px solid transparent;
    cursor: pointer;
    background: none;
    border-top: 0;
    border-left: 0;
    border-right: 0;
    padding: 0;
    text-align: left;
    display: inline-block;
  }}
  .link-btn:hover {{ border-bottom-color: var(--action); }}

  /* Verification section */
  .verify-split {{ align-items: start; }}
  .stat-row {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--s-3);
    margin: 0 0 var(--s-4);
  }}
  .stat-cell {{
    border-top: 1px solid var(--line);
    padding-top: var(--s-2);
  }}
  .stat-cell dt {{ font-size: var(--t-label); color: var(--muted); }}
  .stat-cell dd {{ margin: 2px 0 0; font-size: var(--t-card); font-weight: 500; font-family: var(--font-mono); color: var(--ink); }}
  .verify-copy {{ font-size: var(--t-small); line-height: 1.55; color: var(--ink); margin: 0 0 var(--s-4); }}

  .audit-bar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
    margin-bottom: var(--s-4);
  }}
  .audit-foot {{
    margin-top: var(--s-4);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
  }}
  .audit-foot__actions {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s-4);
  }}

  /* Dark Band: Pipeline Diagram + 4 Open Ruled Composio Proof Columns + Agent vs Human + Rendered Mermaid Proof */
  #agent .section-head {{ margin-bottom: var(--s-5); }}
  #agent .dg-panel {{
    position: relative;
    height: 270px;
    min-height: 270px;
    flex-shrink: 0;
    background: var(--p-inv-surface);
    border: 1px solid color-mix(in srgb, var(--p-inv-ink) 16%, transparent);
    border-radius: var(--r-md);
    padding: 0;
    overflow: clip;
    margin-bottom: var(--s-6);
  }}
  #agent .dg-panel > .dg {{ position: absolute; inset: 0; height: 100%; }}
  .proof-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--gutter);
    margin-bottom: var(--s-6);
  }}
  .proof-col {{
    border-top: 1px solid color-mix(in srgb, var(--p-inv-ink) 22%, transparent);
    padding-top: var(--s-3);
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
  }}
  .proof-col__top {{ display: flex; justify-content: space-between; align-items: center; gap: var(--s-2); }}
  .proof-col__tk {{ display: inline-flex; align-items: center; gap: 8px; }}
  .proof-status {{ font-family: var(--font-mono); font-size: var(--t-label); color: #8fd3c9; }}
  .proof-col__slug {{ font-family: var(--font-mono); font-size: var(--t-label); color: var(--p-inv-ink); margin: 0; overflow-wrap: anywhere; }}
  .proof-meta {{ margin: 0; display: grid; gap: 2px; font-family: var(--font-mono); font-size: var(--t-label); }}
  .proof-meta div {{ display: flex; justify-content: space-between; gap: var(--s-2); }}
  .proof-meta dt {{ color: var(--p-inv-muted); }}
  .proof-meta dd {{ margin: 0; color: var(--p-inv-ink); }}
  .proof-log {{ color: #f0d38c !important; }}
  .proof-col__desc {{ margin: 2px 0 0; font-size: var(--t-small); color: var(--p-inv-ink); line-height: 1.45; }}

  /* Restored Agent vs Human 2-column analysis inside dark band */
  .hitl-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--s-6) var(--gutter);
    margin-bottom: var(--s-6);
  }}
  .hitl-col {{
    border-top: 1px solid color-mix(in srgb, var(--p-inv-ink) 22%, transparent);
    padding-top: var(--s-4);
    min-width: 0;
  }}
  .hitl-col__k {{
    font-family: var(--font-mono);
    font-size: var(--t-label);
    margin: 0 0 var(--s-2);
    color: #8fd3c9;
  }}
  .hitl-col--human .hitl-col__k {{ color: #f0d38c; }}
  .hitl-col h3 {{ color: var(--p-inv-ink); margin: 0 0 var(--s-3); }}
  .hitl-list {{
    display: grid;
    gap: var(--s-3);
    margin: 0;
    padding-left: 18px;
    list-style: disc;
    font-size: var(--t-small);
    line-height: 1.52;
    color: var(--p-inv-ink);
  }}
  .hitl-list strong {{ color: #ffffff; font-weight: 500; }}
  .hitl-list code {{
    font-family: var(--font-mono);
    font-size: 12px;
    padding: 1px 5px;
    border-radius: var(--r-sm);
    background: color-mix(in srgb, var(--p-inv-ink) 12%, transparent);
    color: var(--p-inv-ink);
  }}

  .mermaid-proof {{
    margin-top: 0;
    border: 1px solid color-mix(in srgb, var(--p-inv-ink) 18%, transparent);
    border-radius: var(--r-md);
    padding: var(--s-3) var(--s-4);
    background: var(--p-inv-surface);
  }}
  .mermaid-proof summary {{
    cursor: pointer;
    font-size: var(--t-small);
    font-weight: 500;
    color: var(--p-inv-ink);
    user-select: none;
  }}
  .mermaid-stage {{
    margin-top: var(--s-4);
    padding: var(--s-4);
    background: #101214;
    border: 1px solid color-mix(in srgb, var(--p-inv-ink) 14%, transparent);
    border-radius: var(--r-sm);
    overflow-x: auto;
  }}
  .mermaid-stage svg {{
    max-width: 100%;
    height: auto;
    margin-inline: auto;
  }}
  .mermaid-src-toggle {{
    margin-top: var(--s-3);
    font-size: var(--t-label);
    color: var(--p-inv-muted);
  }}
  .mermaid-proof pre {{
    margin: var(--s-2) 0 0;
    padding: var(--s-3);
    overflow-x: auto;
    max-height: 360px;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 1.5;
    color: var(--p-inv-ink);
    background: #0d0e0f;
    border-radius: var(--r-sm);
  }}

  /* Section 5: Interactive 100-App Research Matrix (Matrix Table + Split Dossier, zero overflow onto footer) */
  .matrix-controls {{
    display: grid;
    grid-template-columns: 2fr repeat(4, minmax(0, 1fr));
    gap: var(--s-3);
    margin-top: 0;
  }}
  .matrix-controls .field {{
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }}
  .matrix-controls label {{
    font-size: var(--t-label);
    font-weight: 500;
    color: var(--muted);
  }}
  .matrix-controls input,
  .matrix-controls select {{
    height: 44px;
    width: 100%;
    padding: 0 var(--s-3);
    border-radius: var(--r-sm);
    border: 1px solid var(--line-strong);
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-text);
    font-size: var(--t-small);
  }}
  .matrix-bar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
    margin: var(--s-3) 0 var(--s-4);
    font-size: var(--t-small);
  }}
  .matrix-checks {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s-4);
  }}
  .matrix-checks label {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    min-height: 40px;
  }}
  .matrix-toolbar-right {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s-3);
  }}
  .matrix-exports {{
    display: flex;
    flex-wrap: wrap;
    gap: var(--s-2);
  }}

  /* Full Multi-Column Matrix Table View */
  .matrix-table-shell {{
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--surface);
    overflow: hidden;
  }}
  .matrix-table {{
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: var(--t-small);
  }}
  .matrix-table th {{
    font-size: var(--t-label);
    font-weight: 500;
    color: var(--muted);
    padding: 11px var(--s-3);
    border-bottom: 1px solid var(--line-strong);
    background: color-mix(in srgb, var(--ink) 3%, var(--surface));
    white-space: nowrap;
  }}
  .matrix-table td {{
    padding: 11px var(--s-3);
    border-bottom: 1px solid var(--line);
    vertical-align: top;
    color: var(--ink);
    line-height: 1.4;
  }}
  .matrix-table tbody tr {{
    cursor: pointer;
    transition: background var(--m-in, 150ms) var(--ease);
  }}
  .matrix-table tbody tr:hover {{
    background: color-mix(in srgb, var(--ink) 4%, var(--bg));
  }}
  .matrix-table tbody tr.is-active {{
    background: var(--bg);
    box-shadow: inset 3px 0 0 var(--action);
  }}
  .matrix-table tbody tr:last-child td {{ border-bottom: 0; }}
  .mt-app {{ display: flex; align-items: flex-start; gap: 10px; min-width: 190px; }}
  .mt-app__name {{ font-weight: 500; color: var(--ink); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
  .mt-app__cat {{ font-size: var(--t-label); color: var(--muted); display: block; }}
  .mt-app__one {{ font-size: 12px; color: var(--muted); margin-top: 2px; max-width: 280px; }}
  .mt-auth {{ display: flex; flex-wrap: wrap; gap: 4px; max-width: 190px; }}
  .mt-pill {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: var(--r-sm);
    font-family: var(--font-mono);
    font-size: 11px;
    background: color-mix(in srgb, var(--ink) 7%, transparent);
    color: var(--ink);
    white-space: nowrap;
  }}
  .mt-pill--audit {{ background: color-mix(in srgb, #0f5257 16%, var(--bg)); color: #0b3d41; }}
  .mt-pill--fix {{ background: color-mix(in srgb, #8c6218 16%, var(--bg)); color: #5c3f0b; }}
  .mt-comp-slugs {{ font-family: var(--font-mono); font-size: 12px; color: var(--action); word-break: break-word; max-width: 170px; }}
  .mt-comp-meta {{ font-size: 11px; color: var(--muted); margin-top: 2px; white-space: nowrap; }}
  .mt-blocker {{ font-size: 12px; color: var(--muted); margin-top: 4px; max-width: 210px; }}
  .matrix-table-foot {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-3);
    padding: var(--s-3) var(--s-4);
    border-top: 1px solid var(--line);
    background: var(--bg);
    font-size: var(--t-small);
  }}
  .matrix-table-foot__nav {{
    display: flex;
    align-items: center;
    gap: var(--s-4);
  }}

  /* Split Dossier App-Frame (bounded sticky sidebar + auto-height dossier, ZERO overflow) */
  .app-frame {{
    display: grid;
    grid-template-columns: 5fr 7fr;
    align-items: start;
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--surface);
    overflow: hidden;
  }}
  .app-frame__side {{
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--line);
    background: var(--bg);
    min-width: 0;
    position: sticky;
    top: calc(var(--nav) + 16px);
    max-height: 820px;
  }}
  .app-frame__list {{
    flex: 1 1 auto;
    min-width: 0;
    overflow-y: auto;
  }}
  .app-pager {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-2);
    padding: var(--s-3) var(--s-4);
    border-top: 1px solid var(--line);
    font-size: var(--t-small);
    background: var(--surface);
    flex-shrink: 0;
  }}
  .app-pager__info {{ font-family: var(--font-mono); font-size: var(--t-label); color: var(--muted); }}
  .app-item {{
    all: unset;
    box-sizing: border-box;
    width: 100%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--s-2);
    padding: 10px var(--s-4);
    border-bottom: 1px solid var(--line);
    min-height: 54px;
    transition: background var(--m-in, 150ms) var(--ease);
  }}
  .app-item:hover {{ background: var(--surface); }}
  .app-item[aria-selected="true"] {{
    background: var(--surface);
    box-shadow: inset 3px 0 0 var(--action);
  }}
  .app-item:focus-visible {{ outline: 2px solid var(--action); outline-offset: -2px; }}
  .app-item__left {{
    display: flex;
    align-items: center;
    gap: var(--s-3);
    min-width: 0;
    flex: 1 1 auto;
  }}
  .app-item__text {{ min-width: 0; }}
  .app-item__num {{
    font-family: var(--font-mono);
    font-size: var(--t-label);
    color: var(--muted);
    width: 24px;
    flex-shrink: 0;
  }}
  .app-item__name {{
    font-size: var(--t-body);
    font-weight: 500;
    color: var(--ink);
    display: block;
    line-height: 1.25;
  }}
  .app-item__cat {{
    font-size: var(--t-label);
    color: var(--muted);
    display: block;
    line-height: 1.3;
  }}
  .app-item .tag {{ flex-shrink: 0; }}

  .app-frame__detail {{
    padding: var(--s-5) var(--s-6);
    background: var(--surface);
    min-width: 0;
    height: auto;
  }}
  .dossier__head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--s-4);
    padding-bottom: var(--s-4);
    border-bottom: 1px solid var(--line);
  }}
  .dossier__title {{
    display: flex;
    align-items: center;
    gap: var(--s-3);
  }}
  .dossier__title h3 {{ margin: 0; color: var(--ink); }}
  .dossier__one {{ font-size: var(--t-body); line-height: 1.55; margin: var(--s-4) 0; color: var(--ink); }}
  .dossier__grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--s-4);
    margin-bottom: var(--s-4);
  }}
  .dossier__block {{
    border-top: 1px solid var(--line);
    padding-top: var(--s-3);
    min-width: 0;
  }}
  .dossier__block h4 {{ font-size: var(--t-label); font-weight: 500; color: var(--muted); margin: 0 0 6px; }}
  .dossier__block p {{ font-size: var(--t-small); line-height: 1.52; margin: 0; color: var(--ink); overflow-wrap: anywhere; }}
  .dossier__block a.link {{ overflow-wrap: anywhere; word-break: break-word; }}
  .dossier__urls {{ list-style: none; margin: 0; padding: 0; }}
  .dossier__urls li {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px var(--s-3);
    padding: 8px 0;
    border-bottom: 1px solid var(--line);
    font-size: var(--t-small);
  }}
  .dossier__urls li:last-child {{ border-bottom: 0; }}
  .dossier__urls a {{
    color: var(--action);
    overflow-wrap: anywhere;
    word-break: break-word;
    flex: 1 1 200px;
    min-width: 0;
  }}
  .dossier__audit {{
    margin-top: var(--s-4);
    padding: var(--s-4);
    background: var(--bg);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    font-size: var(--t-small);
    color: var(--ink);
    overflow-wrap: anywhere;
    word-break: break-word;
  }}
  .dossier__audit ul {{ margin: var(--s-2) 0 0; padding-left: var(--s-4); display: grid; gap: 4px; list-style: disc; }}
  .dossier__audit li {{ overflow-wrap: anywhere; word-break: break-word; }}

  /* Statement section spacing */
  #thesis .mo-wh__text {{ max-width: 28ch; }}

  /* Footer close-word sizing so it fits .wrap cleanly at 1440, 390, and 320 without clipping or spill */
  .close__word {{
    font-size: clamp(44px, 11.5vw, 184px);
    line-height: 1.02;
    overflow: visible;
    max-width: 100%;
  }}

  /* Tablet & mobile responsiveness */
  @media (max-width: 1023px) {{
    .finding-grid, .chart-grid, .proof-grid, .hitl-grid, .dossier__grid {{
      grid-template-columns: 1fr;
    }}
    .matrix-controls {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .matrix-controls .field--search {{ grid-column: 1 / -1; }}
    .stat-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .app-frame {{ grid-template-columns: 1fr; }}
    .app-frame__side {{ position: static; max-height: 360px; border-right: 0; border-bottom: 1px solid var(--line); }}
    .app-frame__detail {{ padding: var(--s-4); }}
    .chart-canvas {{ height: 220px; }}
    .chart-canvas--catalog {{ height: 220px; }}
    .chart-canvas--catbar {{ height: 200px; }}
    .chart-canvas--acc {{ height: 220px; }}
    .chart-canvas--fixes {{ height: 230px; }}
  }}
  @media (max-width: 639px) {{
    main > :is(section, .section) {{ padding: var(--s-7) 0 !important; }}
    .hero-facts {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-3); }}
    .hero__text > * + * {{ margin-top: var(--s-3); }}
    .hero__text > .btn-row {{ margin-top: var(--s-4); }}
    .preview-mcp {{ display: none; }}
    .preview-row {{ padding: var(--s-2) 0; }}
    .audit-window__bar {{ padding: var(--s-2) var(--s-4); }}
    .audit-window__list {{ padding: var(--s-1) var(--s-4); }}
    #agent .dg-panel {{ height: 320px; min-height: 320px; }}
    .dossier__head {{ flex-direction: column; gap: var(--s-2); }}
    .matrix-exports .btn {{ flex: 1 1 auto; }}
  }}
  @media (max-width: 360px) {{
    .nav__logo {{ font-size: 15px; }}
    .nav:not(.is-open) .nav__actions .btn {{ padding-inline: 10px; font-size: 13px; }}
  }}
</style>
</head>
<body>
<!-- type: software
     deal: hero split, palette swap-pastels, type geist, radius sharp, nav nav-centre, close close-word, footer footer-dark, rhythm dark-band, buttons solid, mark wordmark, lit-ground sage, grounds bg-halo(hero) bg-band(patterns)
     moments: word-highlight (#thesis), line-carries-colour (#agent)
     why it moves: hero entrance introduces title then proof window; word-highlight lands the MCP thesis on scroll; line-carries-colour transitions cleanly into the dark live-proof band; lanes diagram pulses live pipeline data flow -->

<header class="nav nav--centre">
  <div class="wrap nav__bar">
    <a class="skip-link" href="#top">Skip to content</a>
    <a class="nav__logo" href="#top">Composio</a>
    <nav class="nav__links" aria-label="Main">
      <div class="nav__item"><a class="nav__link" href="#patterns">Patterns</a></div>
      <div class="nav__item"><a class="nav__link" href="#roadmap">Roadmap</a></div>
      <div class="nav__item"><a class="nav__link" href="#verification">Verification</a></div>
      <div class="nav__item"><a class="nav__link" href="#agent">Pipeline</a></div>
      <div class="nav__item"><a class="nav__link" href="#matrix">Matrix</a></div>
    </nav>
    <div class="nav__actions">
      <a class="btn btn--primary" href="#matrix">Explore 100 apps</a>
    </div>
    <button class="nav__toggle" type="button" aria-expanded="false" aria-label="Menu">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M2 5h14M2 13h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
    </button>
  </div>
</header>

<main id="top">

  <!-- SCREEN 1: DEALT SPLIT HERO -->
  <section class="hero hero--split bg-halo" data-enter aria-labelledby="hero-h">
    <div class="wrap">
      <div class="hero-text grid hero__grid">
        <div class="hero__text span-5">
          <p class="hero__kicker"><span class="dot" aria-hidden="true"></span>100 apps across 10 categories · {cat_sum.get('total_composio_toolkits_scanned', 1842):,} Composio toolkits audited</p>
          <h1 id="hero-h">Toolkit research across 100 SaaS and AI apps</h1>
          <p class="hero__lead">A three-pass Composio, Exa and Gemini pipeline measuring auth methods, access gates, official MCP servers and catalog gaps.</p>
          <div class="btn-row">
            <a class="btn btn--primary" href="#matrix">Explore 100 apps<svg class="m-arrow" viewBox="0 0 12 12" aria-hidden="true"><path class="m-arrow__stem" d="M1 6h8"/><path class="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5"/></svg></a>
            <a class="btn btn--secondary" href="{REPO_URL}" target="_blank" rel="noopener">View source repo</a>
          </div>
          <dl class="hero-facts">
            <div><dt>Ready today</dt><dd>{ready_cnt}/{total}<small>Self-serve &amp; documented</small></dd></div>
            <div><dt>With friction</dt><dd>{friction_cnt}/{total}<small>Paywall or app review</small></dd></div>
            <div><dt>Gated / blocked</dt><dd>{gated_cnt + blocked_cnt}/{total}<small>{gated_cnt} outreach · {blocked_cnt} CLI</small></dd></div>
            <div><dt>Official MCPs</dt><dd>{official_mcp_cnt}/{total}<small>+{comm_mcp_cnt} community only</small></dd></div>
            <div><dt>OAuth2 adoption</dt><dd>{oauth_cnt}%<small>{hl.get('multi_auth_apps', 0)} multi-auth apps</small></dd></div>
            <div><dt>Audit accuracy</dt><dd>{fin_acc}%<small>Up from {p1_acc}% in Pass 1</small></dd></div>
          </dl>
        </div>

        <div class="hero__media audit-window span-6 start-7" data-ui role="region" aria-label="Sample verified records">
          <div class="audit-window__bar">
            <span>final_results.json · 100 verified apps</span>
            <span>{generated_at}</span>
          </div>
          <div class="audit-window__list">
            {''.join(hero_preview_rows)}
          </div>
          <div class="ly-float">
            <div class="ly-float__row"><span class="ly-live">Verified sample</span><span>n={ha_n}</span></div>
            <div class="ly-float__title">Accuracy lifted from {p1_acc}% in Pass 1 to {p2_acc}% in Pass 2 and {fin_acc}% after human review</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- DEALT MOMENT 1: WORD-HIGHLIGHT STATEMENT -->
  <section class="section statement" id="thesis" data-moment="word-highlight" data-moment-opts='{{"from": 0.92, "to": 0.65}}' aria-label="Headline finding">
    <div class="wrap">
      <p class="t-label">Headline finding</p>
      <p class="mo-wh__text">Half of the 100 requested apps are ready to build today, <strong>{official_mcp_cnt} vendors ship official MCP servers</strong>, and {gated_access_cnt} sit behind production review, admin or partner gates that raw LLM research misses.</p>
    </div>
  </section>

  <!-- SECTION 1: PATTERNS & CHARTS -->
  <section class="section g2 bg-band" id="patterns" aria-labelledby="patterns-h">
    <div class="wrap">
      <div class="group">
        <div class="section-head">
          <h2 id="patterns-h">Six patterns across 100 apps. <span class="muted">Dual auth and vendor MCPs now lead.</span></h2>
          <p class="measure">Clustered from 432 live documentation links and 1,842 production Composio toolkit schemas.</p>
        </div>
        <div class="finding-grid">
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 1 · Auth landscape</p><span class="finding__n">{oauth_cnt} OAuth2</span></div>
            <h3>Dual-auth (OAuth2 + API Key/Bearer) is standard</h3>
            <p>OAuth2 appears in {oauth_cnt}/100 apps, followed by API Key ({apikey_cnt}) and Bearer Token ({bearer_cnt}). {hl.get('multi_auth_apps', 0)}/100 apps expose two or more auth schemes, so supporting both managed OAuth and static key fallback unlocks the widest coverage.</p>
          </article>
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 2 · Self-serve wins</p><span class="finding__n">{ready_cnt} ready</span></div>
            <h3>Dev/Infra and Productivity stay nearly 100% open</h3>
            <p>{easiest_cats[0]['category']} and {easiest_cats[1]['category']} deliver the highest density of Ready Today builds, pairing free developer sandboxes, clean OpenAPI/GraphQL specs and instant token provisioning.</p>
          </article>
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 3 · Hidden gate trap</p><span class="finding__n">{gated_access_cnt} gated</span></div>
            <h3>Self-serve portal does not equal production access</h3>
            <p>{gated_access_cnt}/100 apps require app review, paying customer admin accounts or partner contracts—concentrated in {hardest_cats[0]['category']} and {hardest_cats[1]['category']} (Google Ads, Meta Ads, LinkedIn Ads, WhatsApp Business and Amazon SP-API).</p>
          </article>
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 4 · MCP inflection</p><span class="finding__n">{official_mcp_cnt} official</span></div>
            <h3>{official_mcp_cnt}/100 vendors ship official MCP servers</h3>
            <p>Led by {top_mcp_cats[0]['category']} and {top_mcp_cats[1]['category']}, reaching enterprise tools like DealCloud and Otter AI. Several vendors (e.g., Otter AI) gate full REST APIs behind Enterprise while exposing narrower self-serve OAuth MCP endpoints.</p>
          </article>
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 5 · Non-API edge cases</p><span class="finding__n">{blocked_cnt} CLIs</span></div>
            <h3>{blocked_cnt} tools are local CLI binaries, not cloud APIs</h3>
            <p>Sherlock and Mermaid CLI ship no hosted REST API, while YouTube Transcript is a scraper wrapper. Turning them into agent tools requires wrapping a hosted runner (Apify / Mermaid Chart MCP) or a sandboxed workbench.</p>
          </article>
          <article class="finding">
            <div class="finding__top"><p class="finding__k">Pattern 6 · Trigger headroom</p><span class="finding__n">{webhooks_yes} vs {cat_sum.get('with_triggers', 23)}</span></div>
            <h3>Webhooks outpace live Composio event triggers</h3>
            <p>{webhooks_yes} vendors document webhooks, yet only {cat_sum.get('with_triggers', 23)} matched Composio toolkits ship triggers. {len(rm.get('trigger_expansion_candidates', []))} existing Composio toolkits support vendor webhooks today with 0 triggers—a direct retention win.</p>
          </article>
        </div>
      </div>

      <div class="group">
        <div class="section-head">
          <h3>Quantitative breakdown across all 100 apps</h3>
          <p class="measure">Verdict tiers, multi-select auth schemes, and credential gating measured directly from primary docs.</p>
        </div>
        <div class="chart-grid">
          <div class="chart-box">
            <h3>Buildability verdicts</h3>
            <p>Distribution across all {total} apps</p>
            <div class="chart-canvas"><canvas id="chartVerdict" role="img" aria-label="Buildability verdicts chart"></canvas></div>
          </div>
          <div class="chart-box">
            <h3>Auth methods frequency</h3>
            <p>Multi-select counts across {total} apps</p>
            <div class="chart-canvas"><canvas id="chartAuth" role="img" aria-label="Auth methods chart"></canvas></div>
          </div>
          <div class="chart-box">
            <h3>Access and gating model</h3>
            <p>Self-serve tiers versus review and partner walls</p>
            <div class="chart-canvas"><canvas id="chartAccess" role="img" aria-label="Access and gating chart"></canvas></div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- SECTION 2: COMPOSIO ROADMAP & CATEGORY MATRIX -->
  <section class="section g2" id="roadmap" aria-labelledby="roadmap-h">
    <div class="wrap">
      <div class="group">
        <div class="section-head">
          <h2 id="roadmap-h">Composio catalog roadmap. <span class="muted">81 matched, 19 net-new gaps.</span></h2>
          <p class="measure">Live lookup via Composio v3.1 API covering {cat_sum.get('total_tools_across_matched', 14555):,} existing tools, {cat_sum.get('with_composio_managed_oauth', 32)} managed OAuth toolkits and {cat_sum.get('with_triggers', 23)} trigger-enabled apps.</p>
        </div>
        <div class="grid roadmap-split">
          <div class="chart-box span-6">
            <h3>Live Composio catalog split</h3>
            <p>1,842 production toolkits mapped against 100 target apps</p>
            <div class="chart-canvas chart-canvas--catalog"><canvas id="chartCatalog" role="img" aria-label="Composio catalog coverage chart"></canvas></div>
          </div>
          <div class="queue-list span-6">
            <div class="queue-row">
              <div class="queue-row__head">
                <h3>Queue A · Net-new easy wins (build next)</h3>
                <span class="mono-pill">{len(rm.get('net_new_easy_wins', []))} apps</span>
              </div>
              <p>Missing from Composio today, with free or trial credentials and clear public APIs. Click any app to open its dossier:</p>
              <div class="q-links">{queue_links(rm.get('net_new_easy_wins', []), 20)}</div>
            </div>
            <div class="queue-row">
              <div class="queue-row__head">
                <h3>Queue B · Official MCP expansion</h3>
                <span class="mono-pill">{len(rm.get('mcp_expansion_candidates', []))} apps</span>
              </div>
              <p>Built API toolkits in Composio where the vendor now ships an official remote MCP ready to onboard as a sibling:</p>
              <div class="q-links">{queue_links(rm.get('mcp_expansion_candidates', []), 12)}</div>
            </div>
            <div class="queue-row">
              <div class="queue-row__head">
                <h3>Queue C · Net-new friction and outreach</h3>
                <span class="mono-pill">{len(rm.get('net_new_friction', []))} friction · {len(rm.get('net_new_outreach', []))} outreach</span>
              </div>
              <p>Missing from Composio and gated by paid plans, customer admin walls or enterprise sales:</p>
              <div class="q-links">{queue_links(rm.get('net_new_friction', []), 20)}{queue_links(rm.get('net_new_outreach', []), 20, badge="outreach")}</div>
            </div>
            <div class="queue-row">
              <div class="queue-row__head">
                <h3>Queue D · Non-API blockers and trigger gaps</h3>
                <span class="mono-pill">{len(rm.get('net_new_blocked', []))} blocked · {len(rm.get('trigger_expansion_candidates', []))} trigger gaps</span>
              </div>
              <p class="queue-sublabel">Net-new CLI / non-API blockers (require hosted runner or sandbox workbench):</p>
              <div class="q-links">{queue_links(rm.get('net_new_blocked', []), 10)}</div>
              <p class="queue-sublabel">Existing Composio toolkits with vendor webhooks but 0 live triggers:</p>
              <div class="q-links">{queue_links(rm.get('trigger_expansion_candidates', []), 10)}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="group">
        <div class="chart-box roadmap-cat-chart">
          <h3>Readiness and Composio coverage by category</h3>
          <p>Ready-today builds versus live Composio presence across all 10 categories (10 apps each)</p>
          <div class="chart-canvas chart-canvas--catbar"><canvas id="chartCategoryBar" role="img" aria-label="Category readiness and Composio coverage chart"></canvas></div>
        </div>
        <div class="ledger-wrap">
          <table class="ledger">
            <thead>
              <tr>
                <th>Category (10 apps each)</th>
                <th class="td-num">Ready</th>
                <th class="td-num">Friction</th>
                <th class="td-num">Gated</th>
                <th class="td-num">Blocked</th>
                <th class="td-num">Official MCP</th>
                <th class="td-num">OAuth2</th>
                <th class="td-num">In Composio</th>
              </tr>
            </thead>
            <tbody>
              {''.join(cat_rows_html)}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- SECTION 3: VERIFICATION LOOPS & HONEST ACCURACY -->
  <section class="section g2" id="verification" aria-labelledby="verification-h">
    <div class="wrap">
      <div class="group">
        <div class="section-head">
          <h2 id="verification-h">Verification across three passes. <span class="muted">From {p1_acc}% to {fin_acc}% on the audited sample.</span></h2>
          <p class="measure">Every record moved through raw extraction, four automated checks, and a stratified {ha_n}-app human and live-browser audit covering all 10 categories.</p>
        </div>
        <div class="grid verify-split">
          <div class="chart-box span-6">
            <h3>Accuracy progression (n={ha_n})</h3>
            <p>Exact record accuracy across all core fields</p>
            <div class="chart-canvas chart-canvas--acc"><canvas id="chartAccuracy" role="img" aria-label="Accuracy progression across three verification passes"></canvas></div>
          </div>
          <div class="span-6">
            <dl class="stat-row">
              <div class="stat-cell"><dt>Apps fixed</dt><dd>{p2_sum.get('apps_modified', 0)}/{total}</dd></div>
              <div class="stat-cell"><dt>Field fixes</dt><dd>{p2_sum.get('total_field_corrections', 0)}</dd></div>
              <div class="stat-cell"><dt>URLs checked</dt><dd>{hl.get('total_urls_checked', 0)}</dd></div>
              <div class="stat-cell"><dt>Repos audited</dt><dd>{hl.get('github_repos_audited_via_composio', 0)}</dd></div>
            </dl>
            <p class="verify-copy"><strong>Four automated Pass 2 checks:</strong> (1) HTTP link verification separating dead 404/410s from bot-shielded portals; (2) Exa <code>/contents</code> extraction plus disconfirmation search hunting hidden paywalls and MCP launches; (3) live Composio v3.1 catalog cross-check; and (4) live Composio <code>github</code> repo audits checking org ownership, stars and archived flags.</p>
            <div class="chart-box">
              <h3>Pass 2 corrections by field</h3>
              <p>All {p2_sum.get('total_field_corrections', 0)} automated fixes before human review</p>
              <div class="chart-canvas chart-canvas--fixes"><canvas id="chartFixes" role="img" aria-label="Pass 2 field corrections breakdown chart"></canvas></div>
              <div class="fix-pills">{fix_pills_html}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="group">
        <div class="audit-bar">
          <div>
            <h3>Full audit ledger ({ha_n} human-audited apps &amp; {len(pass2_diffs)} Pass 2 diffs)</h3>
            <p class="muted" style="margin: 2px 0 0; font-size: var(--t-small);">Complete untruncated findings across the stratified human/browser sample and automated critic diffs.</p>
          </div>
          <div class="tabs" role="tablist" aria-label="Audit tables">
            <button type="button" class="tab" role="tab" id="tabHuman" aria-selected="true" aria-controls="panelHuman" onclick="switchAuditTab('human')">Human audit ({ha_n})</button>
            <button type="button" class="tab" role="tab" id="tabDiffs" aria-selected="false" aria-controls="panelDiffs" onclick="switchAuditTab('diffs')">Pass 2 diffs ({len(pass2_diffs)})</button>
          </div>
        </div>

        <div id="panelHuman" role="tabpanel" aria-labelledby="tabHuman" class="ledger-wrap">
          <table class="ledger">
            <thead>
              <tr>
                <th>App</th>
                <th class="td-num">Pass 1</th>
                <th class="td-num">Pass 2</th>
                <th>Verification method</th>
                <th>Honest finding (untruncated)</th>
              </tr>
            </thead>
            <tbody>{''.join(ha_rows_html)}</tbody>
          </table>
          <div class="audit-foot">
            <span class="t-small muted" id="humanAuditSummary">Showing top 8 of {ha_n} stratified human-audited apps (human-caught fixes first).</span>
            <div class="audit-foot__actions">
              <button type="button" class="link-btn" id="toggleHumanRows" onclick="toggleLedgerRows('panelHuman', 'toggleHumanRows', 'humanAuditSummary', 8, {ha_n}, 'stratified human-audited apps')">Show all {ha_n} audited apps</button>
              <a href="#matrix" class="link" onclick="jumpWithFilter('audited'); return false;">Filter all {ha_n} in matrix</a>
            </div>
          </div>
        </div>

        <div id="panelDiffs" role="tabpanel" aria-labelledby="tabDiffs" class="ledger-wrap" hidden>
          <table class="ledger">
            <thead>
              <tr>
                <th>App</th>
                <th>Field</th>
                <th>Pass 1 (before)</th>
                <th>Pass 2 (after)</th>
                <th>Primary-source evidence (untruncated)</th>
              </tr>
            </thead>
            <tbody>{''.join(diff_rows_html)}</tbody>
          </table>
          <div class="audit-foot">
            <span class="t-small muted" id="diffSummary">Showing top 10 of {len(pass2_diffs)} automated Pass 2 field corrections.</span>
            <div class="audit-foot__actions">
              <button type="button" class="link-btn" id="toggleDiffRows" onclick="toggleLedgerRows('panelDiffs', 'toggleDiffRows', 'diffSummary', 10, {len(pass2_diffs)}, 'automated Pass 2 field corrections')">Show all {len(pass2_diffs)} diffs</button>
              <a href="#matrix" class="link" onclick="jumpWithFilter('changed'); return false;">Filter all {p2_sum.get('apps_modified', 29)} corrected apps in matrix</a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- SECTION 4: DARK BAND — PULSING DIAGRAM, LIVE COMPOSIO PROOF, AGENT VS HUMAN & RENDERED MERMAID -->
  <section class="section ground-inverse" id="agent" data-moment="line-carries-colour" data-moment-opts='{{"from": "base"}}' aria-labelledby="agent-h">
    <div class="wrap">
      <div class="section-head">
        <h2 id="agent-h">Pipeline, live Composio logs and human-in-the-loop. <span class="muted">Four real tool integrations, zero mocks.</span></h2>
        <p class="measure">Composio Platform SDK v0.34, Exa semantic retrieval, and Gemini structured outputs (Pass 1 and Pass 2 on <code>gemini-4-hydrogen</code>; switched to rate-limited <code>gemini-3.8-flash</code>). Reproduce locally via <code>python src/research_one_composio.py --app "Stripe"</code>.</p>
      </div>
      <div class="dg-panel">
        <div class="dg" data-diagram><script type="application/json">{diagram_spec_json}</script></div>
      </div>
      <div class="proof-grid">
        {''.join(proof_cols_html)}
      </div>

      <div class="hitl-grid">
        <article class="hitl-col">
          <p class="hitl-col__k">90%+ automated</p>
          <h3>Where the agent excelled</h3>
          <ul class="hitl-list">
            <li><strong>Massive parallel primary-source retrieval:</strong> Researched all 100 apps across 200+ Exa semantic queries and verified 432 live doc URLs in minutes rather than days.</li>
            <li><strong>Catching 2025-2026 official MCP launches:</strong> Found newly launched official remote MCP servers (HubSpot, DealCloud, WhatsApp Business, Otter AI, Linear, Stripe, Plaid) that static LLM memory misses.</li>
            <li><strong>Programmatic Composio catalog auditing:</strong> Scanned 1,842 live Composio toolkits via <code>/api/v3.1/toolkits</code> to compute exact tool counts, trigger counts and auth mode cross-checks with zero manual scraping.</li>
            <li><strong>Repo and CLI forensics:</strong> Used Composio <code>deepwiki_mcp</code> and <code>github</code> toolkits to verify whether GitHub MCP repos belong to official vendor orgs versus community forks.</li>
          </ul>
        </article>
        <article class="hitl-col hitl-col--human">
          <p class="hitl-col__k">Real failure modes caught</p>
          <h3>Where a human was essential</h3>
          <ul class="hitl-list">
            <li><strong>Bot-shielded doc portals (caught in 5-app pilot):</strong> Meta (<code>developers.facebook.com</code>), LinkedIn and Cloudflare return HTTP 400/403/timeouts to headless clients. Our initial link checker mistakenly dropped valid WhatsApp URLs and swapped in a <code>?locale=zh_CN</code> page—requiring a human fix combining HTTP checks with Exa <code>/contents</code> status codes.</li>
            <li><strong>Free dev portal vs. production app review:</strong> Pass 1 occasionally labeled Ads and Fintech apps as <code>Self-Serve Free</code> because sandbox signup is free, missing mandatory business verification or developer token review for production.</li>
            <li><strong>Split-surface products:</strong> Products like <strong>Otter AI</strong> (Enterprise-only REST API vs. self-serve 3-tool OAuth MCP) and <strong>NotebookLM</strong> (consumer web app vs. GCP Enterprise API) required human judgment on the buildability rubric.</li>
            <li><strong>Catalog alias disambiguation and obscure portals:</strong> Human and browser review caught false catalog matches (<code>linkedin</code> vs. <code>linkedin_ads</code>; Amazon shopping vs. SP-API), entity confusion (<code>Paygent Connect</code> vs. Payman AI), Clay's 404 HTTP API docs, and FanBasis's rebrand to Commas.</li>
          </ul>
        </article>
      </div>

      <details class="mermaid-proof" id="mermaidProofDetails" ontoggle="if(this.open && window.renderMermaidProof) window.renderMermaidProof()">
        <summary>View full 3-pass architecture diagram (validated via Composio mermaid_chart_mcp · session {html.escape(mermaid_session_id)} · log {html.escape(mermaid_log_id)})</summary>
        <div class="mermaid-stage" id="mermaidDiagramMount">
          <p class="t-small muted">Rendering validated 3-pass flowchart...</p>
        </div>
        <details class="mermaid-src-toggle">
          <summary>Inspect raw Mermaid source validated by log {html.escape(mermaid_log_id)}</summary>
          <pre id="mermaidRawSource">{html.escape(mermaid_code)}</pre>
        </details>
      </details>
    </div>
  </section>

  <!-- SECTION 5: INTERACTIVE 100-APP RESEARCH MATRIX (TABLE + SPLIT DOSSIER, ZERO OVERFLOW) -->
  <section class="section" id="matrix" aria-labelledby="matrix-h">
    <div class="wrap">
      <div class="section-head">
        <h2 id="matrix-h">Interactive 100-app research matrix. <span class="muted">Filter by verdict, auth, MCP or catalog gap.</span></h2>
        <p class="measure">Compare all 100 apps side-by-side in Matrix table view, or click any app to open its full verified dossier, live URL health badges, Composio metadata and Pass 2 diff log.</p>
      </div>

      <div class="matrix-controls">
        <div class="field field--search">
          <label for="searchInput">Search apps</label>
          <input id="searchInput" type="search" placeholder="Name, auth method, blocker or notes">
        </div>
        <div class="field">
          <label for="filterCategory">Category</label>
          <select id="filterCategory"><option value="">All 10 categories</option></select>
        </div>
        <div class="field">
          <label for="filterVerdict">Buildability verdict</label>
          <select id="filterVerdict">
            <option value="">All verdicts</option>
            <option value="Ready Today (Easy Win)">Ready Today (Easy Win)</option>
            <option value="Buildable with Friction">Buildable with Friction</option>
            <option value="Gated / Needs Outreach">Gated / Needs Outreach</option>
            <option value="Blocked / Not API-Native">Blocked / Not API-Native</option>
          </select>
        </div>
        <div class="field">
          <label for="filterMcp">MCP status</label>
          <select id="filterMcp">
            <option value="">All MCP statuses</option>
            <option value="Official MCP">Official MCP</option>
            <option value="Community MCP Only">Community MCP Only</option>
            <option value="None Found">None Found</option>
          </select>
        </div>
        <div class="field">
          <label for="filterComposio">Composio coverage</label>
          <select id="filterComposio">
            <option value="">All Composio coverage</option>
            <option value="Not in Catalog">Not in Catalog (19)</option>
            <option value="Built API Only">Built API Only</option>
            <option value="Both Built + Provider MCP">Both Built + Provider MCP</option>
            <option value="Provider MCP Only">Provider MCP Only</option>
          </select>
        </div>
      </div>

      <div class="matrix-bar">
        <div class="matrix-checks">
          <span id="resultCount" class="td-strong">Showing {total} of {total} apps</span>
          <label><input id="filterChangedOnly" type="checkbox"> Pass 2 corrected</label>
          <label><input id="filterAuditedOnly" type="checkbox"> Human audited</label>
          <button type="button" class="link-btn" onclick="resetFilters()">Reset filters</button>
        </div>
        <div class="matrix-toolbar-right">
          <div class="tabs" role="tablist" aria-label="Matrix view mode">
            <button type="button" class="tab" role="tab" id="viewTabTable" aria-selected="true" aria-controls="matrixTablePanel" onclick="setMatrixView('table')">Matrix table</button>
            <button type="button" class="tab" role="tab" id="viewTabSplit" aria-selected="false" aria-controls="matrixSplitPanel" onclick="setMatrixView('split')">Split dossier</button>
          </div>
          <div class="matrix-exports">
            <button type="button" class="btn btn--secondary" onclick="downloadJSON()">JSON</button>
            <button type="button" class="btn btn--secondary" onclick="downloadCSV()">CSV</button>
            <button type="button" class="btn btn--secondary" id="copyMdBtn" onclick="copyAgentMarkdown()">Copy markdown</button>
          </div>
        </div>
      </div>

      <!-- View 1: Full Multi-Column Matrix Table -->
      <div id="matrixTablePanel" class="matrix-table-shell" role="tabpanel" aria-labelledby="viewTabTable">
        <div class="ledger-wrap">
          <table class="matrix-table">
            <thead>
              <tr>
                <th>#</th>
                <th>App &amp; category</th>
                <th>Auth method(s)</th>
                <th>Access model</th>
                <th>API &amp; MCP</th>
                <th>Buildability verdict</th>
                <th>Composio live</th>
                <th>Docs</th>
              </tr>
            </thead>
            <tbody id="matrixTableBody"></tbody>
          </table>
        </div>
        <div class="matrix-table-foot">
          <span class="app-pager__info" id="tablePageInfo">Page 1 of 5</span>
          <div class="matrix-table-foot__nav">
            <button type="button" class="link-btn" id="tableShowAllBtn" onclick="toggleShowAllTable()">Show all 100 rows</button>
            <button type="button" class="link-btn" id="tablePrevBtn" onclick="changeTablePage(-1)">Previous</button>
            <button type="button" class="link-btn" id="tableNextBtn" onclick="changeTablePage(1)">Next</button>
          </div>
        </div>
      </div>

      <!-- View 2: Split Dossier Workspace -->
      <div id="matrixSplitPanel" class="app-frame" data-ui role="tabpanel" aria-labelledby="viewTabSplit" hidden>
        <div class="app-frame__side">
          <div id="appList" class="app-frame__list" role="listbox" aria-label="Filtered apps"></div>
          <div class="app-pager" aria-label="App list pagination">
            <button type="button" class="link-btn" id="pagePrev" onclick="changePage(-1)">Previous</button>
            <span class="app-pager__info" id="pageInfo">Page 1 of 7</span>
            <button type="button" class="link-btn" id="pageNext" onclick="changePage(1)">Next</button>
          </div>
        </div>
        <div id="appDetail" class="app-frame__detail" aria-live="polite"></div>
      </div>
    </div>
  </section>

</main>

<!-- FOOTER: DEALT close-word + footer-dark (with .ground-inverse) -->
<footer class="footer closing footer--dark ground-inverse" id="contact" aria-labelledby="close-h">
  <div class="wrap">
    <div class="closing__cta close--word">
      <div class="section-head--split">
        <div>
          <h2 id="close-h">Inspect the 100-app dataset</h2>
          <p class="t-lead">Machine-readable JSON, llms.txt index and reproducible Python agents included.</p>
        </div>
        <div class="btn-row">
          <a class="btn btn--primary" href="#matrix">Explore 100 apps<svg class="m-arrow" viewBox="0 0 12 12" aria-hidden="true"><path class="m-arrow__stem" d="M1 6h8"/><path class="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5"/></svg></a>
        </div>
      </div>
      <p class="close__word" aria-hidden="true">Composio</p>
    </div>

    <div class="closing__links">
      <div class="grid">
        <div class="span-4 stack-4">
          <a class="nav__logo" href="#top">Composio</a>
          <p class="footer__lede">AI Product Ops feasibility research across 100 SaaS, developer, fintech and AI apps.</p>
        </div>
        <div class="span-2 start-7 footer__col">
          <h3>Sections</h3>
          <ul>
            <li><a href="#patterns">Patterns</a></li>
            <li><a href="#roadmap">Roadmap</a></li>
            <li><a href="#verification">Verification</a></li>
            <li><a href="#agent">Pipeline</a></li>
          </ul>
        </div>
        <div class="span-2 footer__col">
          <h3>Artifacts</h3>
          <ul>
            <li><a href="llms.txt">llms.txt index</a></li>
            <li><a href="data/final_results.json">final_results.json</a></li>
            <li><a href="data/human_audit.json">human_audit.json</a></li>
            <li><a href="data/composio_catalog_deep.json">catalog_deep.json</a></li>
          </ul>
        </div>
        <div class="span-2 footer__col">
          <h3>Repository</h3>
          <ul>
            <li><a href="{REPO_URL}" target="_blank" rel="noopener">GitHub source</a></li>
            <li><a href="{REPO_URL}/blob/main/README.md" target="_blank" rel="noopener">Runbook README</a></li>
          </ul>
        </div>
      </div>
      <div class="footer__legal">
        <span>&copy; 2026 Composio Product Ops Study</span>
        <span class="credits">Product names are trademarks of their owners. UI icons via Lucide.</span>
      </div>
    </div>
  </div>
</footer>

<!-- Machine-readable 100-app dataset for AI agents and client explorer -->
<script type="application/json" id="composio-100-apps-dataset">{embedded_json_str}</script>

<script type="module" src="assets/system.js"></script>
<script type="module" src="assets/motion/motion.js"></script>
<script type="module" src="assets/layout/layout.js"></script>
<script type="module" src="assets/diagrams/mount.js"></script>

<script type="module">
  let mermaidMod = null;
  let mermaidRendered = false;
  window.renderMermaidProof = async function () {{
    if (mermaidRendered) return;
    const mount = document.getElementById('mermaidDiagramMount');
    const srcEl = document.getElementById('mermaidRawSource');
    if (!mount || !srcEl) return;
    try {{
      if (!mermaidMod) {{
        mermaidMod = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
        mermaidMod.initialize({{
          startOnLoad: false,
          theme: 'base',
          themeVariables: {{
            background: '#101214',
            primaryColor: '#1e282b',
            primaryTextColor: '#e6f0f5',
            primaryBorderColor: '#4c8c91',
            secondaryColor: '#1b1d1f',
            secondaryTextColor: '#c3d7e5',
            secondaryBorderColor: '#4a5560',
            tertiaryColor: '#16181a',
            tertiaryTextColor: '#c3d7e5',
            tertiaryBorderColor: '#3a424a',
            lineColor: '#8fd3c9',
            clusterBkg: '#161b1d',
            clusterBorder: '#3c5c61',
            fontFamily: '"Geist", system-ui, sans-serif',
            fontSize: '14px'
          }}
        }});
      }}
      const code = srcEl.textContent.trim();
      const {{ svg }} = await mermaidMod.render('composioPipelineSvg', code);
      mount.innerHTML = svg;
      mermaidRendered = true;
    }} catch (err) {{
      mount.innerHTML = '<p class="t-small muted">Could not load Mermaid renderer offline. Inspect the validated raw Mermaid source below.</p>';
    }}
  }};
</script>

<script>
  const PAYLOAD = JSON.parse(document.getElementById('composio-100-apps-dataset').textContent);
  const APPS = PAYLOAD.apps;
  const ANALYTICS = PAYLOAD.analytics;
  const HUMAN_AUDIT = PAYLOAD.human_audit || {{}};
  let selectedId = APPS[0] ? APPS[0].id : 1;
  let currentPage = 0;
  let tablePage = 0;
  let showAllTableRows = false;
  let matrixView = 'table';

  function pageSize() {{
    return window.innerWidth < 640 ? 6 : 15;
  }}

  function tablePageSize() {{
    return showAllTableRows ? 1000 : 20;
  }}

  function esc(s) {{
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }}

  function verdictTag(v) {{
    if (v.startsWith('Ready')) return `<span class="tag tag--ready">Ready today</span>`;
    if (v.startsWith('Buildable')) return `<span class="tag tag--friction">Friction</span>`;
    if (v.startsWith('Gated')) return `<span class="tag tag--gated">Gated</span>`;
    return `<span class="tag tag--blocked">Blocked</span>`;
  }}

  function toggleQueue(btn) {{
    const wrap = btn.closest('.q-links');
    if (!wrap) return;
    const expanded = wrap.classList.toggle('is-expanded');
    btn.textContent = expanded ? btn.dataset.less : btn.dataset.more;
  }}

  function toggleLedgerRows(panelId, btnId, summaryId, defaultCount, totalCount, label) {{
    const panel = document.getElementById(panelId);
    const btn = document.getElementById(btnId);
    const sum = document.getElementById(summaryId);
    if (!panel || !btn) return;
    const expanded = panel.classList.toggle('is-expanded');
    btn.textContent = expanded ? `Show top ${{defaultCount}}` : `Show all ${{totalCount}} ${{label.includes('diff') ? 'diffs' : 'audited apps'}}`;
    if (sum) {{
      sum.textContent = expanded
        ? `Showing all ${{totalCount}} ${{label}}.`
        : `Showing top ${{defaultCount}} of ${{totalCount}} ${{label}}.`;
    }}
  }}

  function setMatrixView(mode) {{
    matrixView = mode === 'split' ? 'split' : 'table';
    const isTable = matrixView === 'table';
    document.getElementById('viewTabTable').setAttribute('aria-selected', String(isTable));
    document.getElementById('viewTabSplit').setAttribute('aria-selected', String(!isTable));
    document.getElementById('matrixTablePanel').hidden = !isTable;
    document.getElementById('matrixSplitPanel').hidden = isTable;
  }}

  // Populate category filter
  const catSel = document.getElementById('filterCategory');
  [...new Set(APPS.map(a => a.category))].forEach(c => {{
    const o = document.createElement('option');
    o.value = c;
    o.textContent = c;
    catSel.appendChild(o);
  }});

  function getFilteredApps() {{
    const q = document.getElementById('searchInput').value.trim().toLowerCase();
    const cat = document.getElementById('filterCategory').value;
    const verd = document.getElementById('filterVerdict').value;
    const mcp = document.getElementById('filterMcp').value;
    const comp = document.getElementById('filterComposio').value;
    const changedOnly = document.getElementById('filterChangedOnly').checked;
    const auditedOnly = document.getElementById('filterAuditedOnly').checked;

    return APPS.filter(a => {{
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
  }}

  function renderDetail(id) {{
    const a = APPS.find(x => x.id === id) || APPS[0];
    if (!a) return;
    selectedId = a.id;

    const urls = (a.evidence_urls || []).map(u => {{
      const st = (a.url_health && a.url_health[u]) ?? '';
      const pill = st ? `<span class="mono-pill">HTTP ${{esc(st)}}</span>` : '';
      return `<li><a href="${{esc(u)}}" target="_blank" rel="noopener">${{esc(u)}}</a>${{pill}}</li>`;
    }}).join('');

    const gh = (a.github_mcp_audit && !a.github_mcp_audit.error)
      ? `<div class="dossier__audit"><strong>Live Composio GitHub audit (${{esc(a.github_mcp_audit.composio_log_id)}})</strong><p style="margin:6px 0 0;font-family:var(--font-mono);font-size:13px;">${{esc(a.github_mcp_audit.repo)}} · ${{esc(a.github_mcp_audit.owner_type)}} · ${{esc(a.github_mcp_audit.stars)}} stars · archived: ${{esc(a.github_mcp_audit.archived)}}</p></div>`
      : '';

    const changes = (a.verification_changes && a.verification_changes.length)
      ? `<div class="dossier__audit"><strong>Verification log (${{a.verification_changes.length}} update${{a.verification_changes.length > 1 ? 's' : ''}})</strong><ul>${{a.verification_changes.map(c => `<li>${{esc(c)}}</li>`).join('')}}</ul></div>`
      : `<div class="dossier__audit"><strong>Verification status:</strong> Confirmed unchanged across Pass 2 automated checks.</div>`;

    document.getElementById('appDetail').innerHTML = `
      <div class="dossier__head">
        <div>
          <span class="mono-pill">#${{a.id}} · ${{esc(a.category)}}</span>
          <div class="dossier__title" style="margin-top:10px;">
            <h3>${{esc(a.name)}}</h3>
          </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;">
          ${{verdictTag(a.buildability_verdict)}}
          <span class="mono-pill">${{esc(a.mcp_status)}}</span>
          ${{a.human_audited ? '<span class="tag tag--ready">Human audited</span>' : ''}}
        </div>
      </div>

      <p class="dossier__one">${{esc(a.one_liner)}}</p>

      <div class="dossier__grid">
        <div class="dossier__block">
          <h4>Authentication (${{(a.auth_methods || []).join(', ')}})</h4>
          <p>${{esc(a.auth_notes)}}</p>
        </div>
        <div class="dossier__block">
          <h4>Access model (${{esc(a.access_model)}})</h4>
          <p>${{esc(a.access_notes)}}</p>
        </div>
        <div class="dossier__block">
          <h4>API surface (${{esc(a.api_protocol)}} · ${{esc(a.api_breadth)}})</h4>
          <p>${{esc(a.api_surface_notes)}}</p>
          <p style="margin-top:6px;color:var(--muted);">OpenAPI: ${{esc(a.openapi_spec_available)}} · Webhooks: ${{esc(a.webhooks_supported)}}</p>
        </div>
        <div class="dossier__block">
          <h4>Composio live catalog (${{esc(a.composio_coverage || 'Not in Catalog')}})</h4>
          <p>Slugs: <code>${{(a.composio_catalog_slugs || []).join(', ') || 'None'}}</code></p>
          <p style="margin-top:4px;">Tools: <strong>${{a.composio_tools_count || 0}}</strong> · Triggers: <strong>${{a.composio_triggers_count || 0}}</strong> · Managed OAuth: <strong>${{a.composio_managed_auth ? 'Yes' : 'No'}}</strong></p>
          <p style="margin-top:4px;color:var(--muted);">Prod auth: ${{(a.composio_auth_modes || []).join(', ') || 'None'}}</p>
        </div>
      </div>

      <div class="dossier__block" style="margin-bottom:var(--s-4);">
        <h4>Primary blocker or friction</h4>
        <p>${{esc(a.primary_blocker)}}</p>
      </div>

      ${{a.mcp_evidence_url ? `<div class="dossier__block" style="margin-bottom:var(--s-4);"><h4>MCP documentation link</h4><p><a class="link" href="${{esc(a.mcp_evidence_url)}}" target="_blank" rel="noopener">${{esc(a.mcp_evidence_url)}}</a></p></div>` : ''}}

      <div class="dossier__block">
        <h4>Verified primary-source URLs</h4>
        <ul class="dossier__urls">${{urls}}</ul>
      </div>

      ${{gh}}
      ${{changes}}
    `;

    document.querySelectorAll('.app-item').forEach(el => {{
      el.setAttribute('aria-selected', String(Number(el.dataset.id) === selectedId));
    }});
    document.querySelectorAll('#matrixTableBody tr').forEach(tr => {{
      tr.classList.toggle('is-active', Number(tr.dataset.id) === selectedId);
    }});
  }}

  function openInSplitDossier(id) {{
    const filtered = getFilteredApps();
    const idx = filtered.findIndex(x => x.id === id);
    selectedId = id;
    currentPage = idx >= 0 ? Math.floor(idx / pageSize()) : 0;
    setMatrixView('split');
    renderList();
    document.getElementById('matrix').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  function renderMatrixTable(filtered) {{
    const tbody = document.getElementById('matrixTableBody');
    const infoEl = document.getElementById('tablePageInfo');
    const prevBtn = document.getElementById('tablePrevBtn');
    const nextBtn = document.getElementById('tableNextBtn');
    const allBtn = document.getElementById('tableShowAllBtn');

    if (!filtered.length) {{
      tbody.innerHTML = '<tr><td colspan="8" style="padding:24px;color:var(--muted);">No apps match these filters.</td></tr>';
      infoEl.textContent = '0 apps';
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      allBtn.hidden = true;
      return;
    }}

    const perPage = tablePageSize();
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    if (tablePage >= totalPages) tablePage = 0;
    const start = tablePage * perPage;
    const slice = filtered.slice(start, start + perPage);

    infoEl.textContent = showAllTableRows
      ? `Showing all ${{filtered.length}} filtered apps`
      : `Page ${{tablePage + 1}} of ${{totalPages}} (${{start + 1}}-${{Math.min(filtered.length, start + slice.length)}} of ${{filtered.length}})`;
    prevBtn.disabled = showAllTableRows || tablePage <= 0;
    nextBtn.disabled = showAllTableRows || tablePage >= totalPages - 1;
    allBtn.hidden = filtered.length <= 20;
    allBtn.textContent = showAllTableRows ? 'Paginate (20/page)' : `Show all ${{filtered.length}} rows`;

    tbody.innerHTML = slice.map(a => {{
      const firstUrl = (a.evidence_urls && a.evidence_urls[0]) || '#';
      const auditTag = a.human_audited ? '<span class="mt-pill mt-pill--audit">Audited</span>' : '';
      const fixTag = (a.verification_changes && a.verification_changes.length)
        ? `<span class="mt-pill mt-pill--fix">${{a.verification_changes.length}} fix</span>` : '';
      const compHtml = (a.composio_catalog_slugs && a.composio_catalog_slugs.length)
        ? `<div class="mt-comp-slugs">${{a.composio_catalog_slugs.map(esc).join(', ')}}</div><div class="mt-comp-meta">${{a.composio_tools_count || 0}} tools · ${{a.composio_triggers_count || 0}} triggers</div>`
        : `<span class="tag tag--gated">Not in catalog</span>`;
      const blockerHtml = (a.primary_blocker && a.primary_blocker !== 'None')
        ? `<div class="mt-blocker">${{esc(a.primary_blocker)}}</div>` : '';
      return `
        <tr data-id="${{a.id}}" class="${{a.id === selectedId ? 'is-active' : ''}}" onclick="openInSplitDossier(${{a.id}})">
          <td class="mono-cell">${{String(a.id).padStart(2, '0')}}</td>
          <td>
            <div class="mt-app">
              <div>
                <div class="mt-app__name">${{esc(a.name)}} ${{auditTag}} ${{fixTag}}</div>
                <span class="mt-app__cat">${{esc(a.category)}}</span>
                <div class="mt-app__one">${{esc(a.one_liner)}}</div>
              </div>
            </div>
          </td>
          <td><div class="mt-auth">${{(a.auth_methods || []).map(m => `<span class="mt-pill">${{esc(m)}}</span>`).join('')}}</div></td>
          <td>${{esc(a.access_model)}}</td>
          <td>
            <div>${{esc(a.api_protocol)}}</div>
            <div style="margin-top:4px;"><span class="mt-pill">${{esc(a.mcp_status)}}</span></div>
          </td>
          <td>
            ${{verdictTag(a.buildability_verdict)}}
            ${{blockerHtml}}
          </td>
          <td>${{compHtml}}</td>
          <td onclick="event.stopPropagation()" style="white-space:nowrap;">
            <a class="link-btn" href="${{esc(firstUrl)}}" target="_blank" rel="noopener">Docs</a>
            <div class="mt-comp-meta">${{(a.evidence_urls || []).length}} link${{(a.evidence_urls || []).length === 1 ? '' : 's'}}</div>
          </td>
        </tr>
      `;
    }}).join('');
  }}

  function renderList() {{
    const filtered = getFilteredApps();
    document.getElementById('resultCount').textContent = `Showing ${{filtered.length}} of ${{APPS.length}} apps`;

    renderMatrixTable(filtered);

    const listEl = document.getElementById('appList');
    const pageInfoEl = document.getElementById('pageInfo');
    const prevBtn = document.getElementById('pagePrev');
    const nextBtn = document.getElementById('pageNext');

    if (!filtered.length) {{
      listEl.innerHTML = '<div style="padding:24px;color:var(--muted);">No apps match these filters.</div>';
      document.getElementById('appDetail').innerHTML = '<p class="muted">Adjust your filters to inspect an app dossier.</p>';
      pageInfoEl.textContent = 'Page 0 of 0';
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      return;
    }}

    const perPage = pageSize();
    const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
    const selIdx = filtered.findIndex(x => x.id === selectedId);
    if (selIdx === -1) {{
      selectedId = filtered[0].id;
      currentPage = 0;
    }} else if (currentPage >= totalPages) {{
      currentPage = Math.floor(selIdx / perPage);
    }}

    const start = currentPage * perPage;
    const slice = filtered.slice(start, start + perPage);
    pageInfoEl.textContent = `Page ${{currentPage + 1}} of ${{totalPages}}`;
    prevBtn.disabled = currentPage <= 0;
    nextBtn.disabled = currentPage >= totalPages - 1;

    listEl.innerHTML = slice.map(a => `
      <button type="button" class="app-item" role="option" data-id="${{a.id}}" aria-selected="${{a.id === selectedId}}" onclick="renderDetail(${{a.id}})">
        <span class="app-item__left">
          <span class="app-item__num">${{String(a.id).padStart(2, '0')}}</span>
          <span class="app-item__text">
            <span class="app-item__name">${{esc(a.name)}}</span>
            <span class="app-item__cat">${{esc(a.category)}}</span>
          </span>
        </span>
        ${{verdictTag(a.buildability_verdict)}}
      </button>
    `).join('');

    renderDetail(selectedId);
  }}

  function changePage(delta) {{
    currentPage = Math.max(0, currentPage + delta);
    renderList();
  }}

  function changeTablePage(delta) {{
    tablePage = Math.max(0, tablePage + delta);
    renderList();
    document.getElementById('matrixTablePanel').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
  }}

  function toggleShowAllTable() {{
    showAllTableRows = !showAllTableRows;
    tablePage = 0;
    renderList();
  }}

  function selectAppAndJump(id) {{
    resetFilters(false);
    selectedId = id;
    const idx = APPS.findIndex(x => x.id === id);
    currentPage = idx >= 0 ? Math.floor(idx / pageSize()) : 0;
    setMatrixView('split');
    renderList();
    document.getElementById('matrix').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  function jumpWithFilter(kind) {{
    resetFilters(false);
    if (kind === 'audited') document.getElementById('filterAuditedOnly').checked = true;
    if (kind === 'changed') document.getElementById('filterChangedOnly').checked = true;
    currentPage = 0;
    tablePage = 0;
    setMatrixView('table');
    renderList();
    document.getElementById('matrix').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}

  function resetFilters(shouldRender = true) {{
    document.getElementById('searchInput').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterVerdict').value = '';
    document.getElementById('filterMcp').value = '';
    document.getElementById('filterComposio').value = '';
    document.getElementById('filterChangedOnly').checked = false;
    document.getElementById('filterAuditedOnly').checked = false;
    currentPage = 0;
    tablePage = 0;
    if (shouldRender) renderList();
  }}

  function switchAuditTab(which) {{
    const isHuman = which === 'human';
    document.getElementById('tabHuman').setAttribute('aria-selected', String(isHuman));
    document.getElementById('tabDiffs').setAttribute('aria-selected', String(!isHuman));
    document.getElementById('panelHuman').hidden = !isHuman;
    document.getElementById('panelDiffs').hidden = isHuman;
  }}

  ['searchInput','filterCategory','filterVerdict','filterMcp','filterComposio','filterChangedOnly','filterAuditedOnly'].forEach(id => {{
    document.getElementById(id).addEventListener('input', () => {{ currentPage = 0; tablePage = 0; renderList(); }});
    document.getElementById(id).addEventListener('change', () => {{ currentPage = 0; tablePage = 0; renderList(); }});
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
    btn.textContent = 'Copied markdown';
    setTimeout(() => btn.textContent = 'Copy markdown', 1800);
  }}

  // Charts strictly using swap-pastels palette tokens (zero violet; autoSkip: false on all categorical axes so zero labels disappear)
  Chart.defaults.font.family = '"Geist", system-ui, sans-serif';
  Chart.defaults.font.size = 13;
  Chart.defaults.color = '#141414';

  const vd = ANALYTICS.distributions.buildability_verdicts || {{}};
  new Chart(document.getElementById('chartVerdict'), {{
    type: 'doughnut',
    data: {{
      labels: ['Ready today', 'Friction', 'Gated', 'Blocked'],
      datasets: [{{
        data: [vd['Ready Today (Easy Win)']||0, vd['Buildable with Friction']||0, vd['Gated / Needs Outreach']||0, vd['Blocked / Not API-Native']||0],
        backgroundColor: ['#0f5257', '#8c6218', '#8f2d2d', '#4a5068'],
        borderColor: '#d0e0eb',
        borderWidth: 2
      }}]
    }},
    options: {{ animation: false, responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, padding: 12 }} }} }} }}
  }});

  const ad = ANALYTICS.distributions.auth_methods || {{}};
  const authEntries = Object.entries(ad).slice(0, 6);
  new Chart(document.getElementById('chartAuth'), {{
    type: 'bar',
    data: {{
      labels: authEntries.map(e => e[0]),
      datasets: [{{ data: authEntries.map(e => e[1]), backgroundColor: '#0f5257', borderRadius: 3 }}]
    }},
    options: {{ animation: false, indexAxis: 'y', responsive: true, maintainAspectRatio: false, layout: {{ padding: {{ left: 10, right: 8 }} }}, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: 'rgba(20,20,20,0.08)' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false }} }} }} }}
  }});

  const ac = ANALYTICS.distributions.access_models || {{}};
  const accEntries = Object.entries(ac);
  const shortAccess = (lbl) => {{
    if (lbl.includes('Admin')) return 'Admin / Customer';
    if (lbl.includes('Partner')) return 'Partner / Sales';
    if (lbl.includes('Review')) return 'App Review';
    if (lbl.includes('Paid')) return 'SS: Paid Plan';
    if (lbl.includes('Free')) return 'SS: Free / Trial';
    if (lbl.includes('Open-Source')) return 'Open-Source / Local';
    return lbl.replace('Self-Serve ', 'SS: ');
  }};
  new Chart(document.getElementById('chartAccess'), {{
    type: 'bar',
    data: {{
      labels: accEntries.map(e => shortAccess(e[0])),
      datasets: [{{ data: accEntries.map(e => e[1]), backgroundColor: ['#0f5257','#2b6d73','#8c6218','#5c667a','#8f2d2d','#141414'], borderRadius: 3 }}]
    }},
    options: {{ animation: false, indexAxis: 'y', responsive: true, maintainAspectRatio: false, layout: {{ padding: {{ left: 10, right: 8 }} }}, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: 'rgba(20,20,20,0.08)' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false }} }} }} }}
  }});

  const cc = ANALYTICS.distributions.composio_coverage || {{}};
  new Chart(document.getElementById('chartCatalog'), {{
    type: 'bar',
    data: {{
      labels: ['Built API only', 'Built + MCP', 'Not in catalog', 'MCP only'],
      datasets: [{{
        data: [cc['Built API Only']||0, cc['Both Built + Provider MCP']||0, cc['Not in Catalog']||0, cc['Provider MCP Only']||0],
        backgroundColor: ['#0f5257', '#2b6d73', '#8c6218', '#4a5068'],
        borderRadius: 3
      }}]
    }},
    options: {{ animation: false, indexAxis: 'y', responsive: true, maintainAspectRatio: false, layout: {{ padding: {{ left: 10, right: 8 }} }}, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ grid: {{ color: 'rgba(20,20,20,0.08)' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false }} }} }} }}
  }});

  const cmList = ANALYTICS.category_matrix || [];
  new Chart(document.getElementById('chartCategoryBar'), {{
    type: 'bar',
    data: {{
      labels: cmList.map(c => c.category.split(' ')[0].replace(',', '')),
      datasets: [
        {{ label: 'Ready today', data: cmList.map(c => c.ready_today), backgroundColor: '#0f5257', borderRadius: 3 }},
        {{ label: 'In Composio', data: cmList.map(c => c.in_composio), backgroundColor: '#4a5068', borderRadius: 3 }}
      ]
    }},
    options: {{ animation: false, responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, padding: 10 }} }} }}, scales: {{ y: {{ min: 0, max: 10, ticks: {{ stepSize: 2 }}, grid: {{ color: 'rgba(20,20,20,0.08)' }} }}, x: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false }} }} }} }}
  }});

  const haS = HUMAN_AUDIT.summary || {{}};
  new Chart(document.getElementById('chartAccuracy'), {{
    type: 'bar',
    data: {{
      labels: ['Pass 1 (Raw)', 'Pass 2 (Auto)', 'Final audited'],
      datasets: [{{
        label: 'Verified accuracy (%)',
        data: [haS.pass1_accuracy_pct || 0, haS.pass2_accuracy_pct || 0, haS.final_accuracy_pct || 0],
        backgroundColor: ['#8f2d2d', '#8c6218', '#0f5257'],
        borderRadius: 3
      }}]
    }},
    options: {{ animation: false, responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }} }}, x: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false }} }} }} }}
  }});

  const fixMap = (ANALYTICS.verification && ANALYTICS.verification.pass2_diff_summary && ANALYTICS.verification.pass2_diff_summary.corrections_by_field) || {{}};
  const fixEntries = Object.entries(fixMap);
  new Chart(document.getElementById('chartFixes'), {{
    type: 'bar',
    data: {{
      labels: fixEntries.map(e => e[0].replace(/_/g, ' ')),
      datasets: [{{ data: fixEntries.map(e => e[1]), backgroundColor: '#0f5257', borderRadius: 3 }}]
    }},
    options: {{ animation: false, indexAxis: 'y', responsive: true, maintainAspectRatio: false, layout: {{ padding: {{ left: 12, right: 8 }} }}, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ stepSize: 2 }}, grid: {{ color: 'rgba(20,20,20,0.08)' }} }}, y: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false, font: {{ size: 12 }} }} }} }} }}
  }});

  renderList();
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
    (ROOT / "index.html").write_text(html_content, encoding="utf-8", newline="\n")

    llms_content = build_llms_txt(records, analytics, human_audit)
    (ROOT / "llms.txt").write_text(llms_content, encoding="utf-8", newline="\n")

    print(f"Built tasteskill index.html ({len(html_content):,} bytes) and llms.txt ({len(llms_content):,} bytes) for {len(records)} apps.")


if __name__ == "__main__":
    main()
