"""
Query Composio's live Platform API via a Session (`session.toolkits()`) to build
a complete lookup table of existing Composio Built toolkits and Provider MCP
(`_mcp`) toolkits, then cross-reference them against our 100 target apps.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
APPS_PATH = ROOT / "data" / "apps.json"
OUT_PATH = ROOT / "data" / "composio_catalog_match.json"


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def fetch_all_toolkits() -> list[dict]:
    composio = Composio()
    session = composio.create(user_id="product_ops_researcher")
    all_items: list[dict] = []
    cursor: str | None = None
    while True:
        kwargs = {"limit": 50}
        if cursor:
            kwargs["next_cursor"] = cursor
        page = session.toolkits(**kwargs)
        items = getattr(page, "items", []) or []
        for item in items:
            all_items.append({
                "slug": getattr(item, "slug", None),
                "name": getattr(item, "name", None),
                "is_no_auth": getattr(item, "is_no_auth", None),
                "composio_managed_auth_schemes": getattr(item, "composio_managed_auth_schemes", None),
            })
        cursor = getattr(page, "next_cursor", None)
        if not cursor:
            break
    return all_items


def match_apps(apps: list[dict], toolkits: list[dict]) -> dict:
    # Build indexes by normalized slug and normalized name
    by_norm_slug: dict[str, list[dict]] = {}
    by_norm_name: dict[str, list[dict]] = {}
    for tk in toolkits:
        slug = tk.get("slug") or ""
        name = tk.get("name") or ""
        base_slug = slug[:-4] if slug.endswith("_mcp") else slug
        by_norm_slug.setdefault(normalize(base_slug), []).append(tk)
        by_norm_slug.setdefault(normalize(slug), []).append(tk)
        if name:
            by_norm_name.setdefault(normalize(name), []).append(tk)

    # Explicit alias map for multi-word / branded names so matching is exact
    aliases = {
        "Salesforce": ["salesforce"],
        "HubSpot": ["hubspot"],
        "Pipedrive": ["pipedrive"],
        "Attio": ["attio"],
        "Twenty": ["twenty"],
        "Podio": ["podio"],
        "Zoho CRM": ["zoho", "zohocrm"],
        "Close": ["close", "closeio"],
        "Copper": ["copper"],
        "DealCloud": ["dealcloud"],
        "Zendesk": ["zendesk"],
        "Intercom": ["intercom"],
        "Freshdesk": ["freshdesk"],
        "Front": ["front"],
        "Pylon": ["pylon"],
        "LiveAgent": ["liveagent"],
        "Plain": ["plain"],
        "Help Scout": ["helpscout"],
        "Gorgias": ["gorgias"],
        "Gladly": ["gladly"],
        "Slack": ["slack", "slackbot"],
        "Twilio": ["twilio"],
        "Zoho Cliq": ["zohocliq"],
        "Lark (Larksuite)": ["lark", "larksuite"],
        "Pumble": ["pumble"],
        "Discord": ["discord", "discordbot"],
        "Telegram": ["telegram"],
        "WhatsApp Business": ["whatsapp"],
        "Aircall": ["aircall"],
        "Vonage": ["vonage"],
        "Google Ads": ["googleads"],
        "Meta Ads": ["metaads", "facebookads", "facebookmarketing"],
        "LinkedIn Ads": ["linkedinads"],
        "GoHighLevel": ["gohighlevel", "highlevel"],
        "Mailchimp": ["mailchimp"],
        "Klaviyo": ["klaviyo"],
        "systeme.io": ["systemeio", "systeme"],
        "Pinterest": ["pinterest"],
        "Threads (Meta)": ["threads"],
        "SendGrid": ["sendgrid"],
        "Shopify": ["shopify"],
        "WooCommerce": ["woocommerce"],
        "BigCommerce": ["bigcommerce"],
        "Salesforce Commerce Cloud": ["salesforcecommercecloud", "sfcc"],
        "Magento (Adobe Commerce)": ["magento", "adobecommerce"],
        "Squarespace": ["squarespace"],
        "Ecwid": ["ecwid"],
        "Gumroad": ["gumroad"],
        "Amazon Selling Partner": ["amazonsellingpartner", "amazonsp", "amazon"],
        "fanbasis": ["fanbasis"],
        "DataForSEO": ["dataforseo"],
        "SE Ranking": ["seranking"],
        "Ahrefs": ["ahrefs"],
        "MrScraper": ["mrscraper"],
        "Apify": ["apify"],
        "Firecrawl": ["firecrawl"],
        "Bright Data": ["brightdata"],
        "Sherlock": ["sherlock"],
        "Waterfall.io": ["waterfall", "waterfallio"],
        "Clay": ["clay"],
        "GitHub": ["github"],
        "Vercel": ["vercel"],
        "Netlify": ["netlify"],
        "Cloudflare": ["cloudflare"],
        "Supabase": ["supabase"],
        "Neo4j": ["neo4j"],
        "Snowflake": ["snowflake"],
        "MongoDB Atlas": ["mongodb", "mongodbatlas"],
        "Datadog": ["datadog"],
        "Sentry": ["sentry"],
        "Notion": ["notion"],
        "Airtable": ["airtable"],
        "Linear": ["linear"],
        "Jira": ["jira"],
        "Asana": ["asana"],
        "Monday.com": ["monday", "mondaycom"],
        "ClickUp": ["clickup"],
        "Coda": ["coda"],
        "Smartsheet": ["smartsheet"],
        "Harvest": ["harvest"],
        "Stripe": ["stripe"],
        "Plaid": ["plaid"],
        "Binance": ["binance"],
        "Paygent Connect": ["paygent", "paygentconnect"],
        "iPayX": ["ipayx"],
        "QuickBooks": ["quickbooks"],
        "Xero": ["xero"],
        "Brex": ["brex"],
        "Ramp": ["ramp"],
        "PitchBook": ["pitchbook"],
        "NotebookLM": ["notebooklm"],
        "Otter AI": ["otter", "otterai"],
        "Fathom": ["fathom"],
        "Consensus": ["consensus"],
        "Reducto": ["reducto"],
        "Devin": ["devin"],
        "higgsfield": ["higgsfield"],
        "Mermaid CLI": ["mermaid", "mermaidcli"],
        "YouTube Transcript": ["youtubetranscript", "transcriptapi"],
        "Grain": ["grain"],
    }

    matches: dict[str, list[dict]] = {}
    matched_count = 0
    for app in apps:
        name = app["name"]
        keys = aliases.get(name, [normalize(name)])
        seen_slugs: set[str] = set()
        found: list[dict] = []
        for k in keys:
            for tk in by_norm_slug.get(k, []) + by_norm_name.get(k, []):
                s = tk["slug"]
                if s not in seen_slugs:
                    seen_slugs.add(s)
                    found.append(tk)
        matches[name] = found
        if found:
            matched_count += 1

    return {
        "total_composio_toolkits_scanned": len(toolkits),
        "apps_matched_in_composio": matched_count,
        "apps_not_in_composio": len(apps) - matched_count,
        "matches": matches,
    }


if __name__ == "__main__":
    print("Fetching Composio live toolkit catalog...")
    toolkits = fetch_all_toolkits()
    print(f"Total toolkits in Composio catalog: {len(toolkits)}")
    apps = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    report = match_apps(apps, toolkits)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Matched {report['apps_matched_in_composio']}/100 apps in Composio live catalog.")
    print(f"Saved to {OUT_PATH}")
