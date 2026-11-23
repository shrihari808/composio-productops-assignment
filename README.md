# Composio AI Product Ops — 100-App Research & Verification Agent

Automated multi-pass research and verification pipeline evaluating 100 SaaS/developer/AI apps across 10 categories for AI agent toolkit and MCP buildability.

## Architecture (WIP — Setup & 5-App Pilot Complete)

1. **Composio Platform SDK (`src/composio_tools.py`, `src/fetch_composio_catalog.py`)**
   - Uses user-scoped Composio Sessions (`composio.create(user_id=...)`) to:
     - Cross-reference all 100 target apps against Composio's live catalog (1,842 toolkits scanned → 81 matched, 19 net-new gaps).
     - Discover and execute live Provider MCP tools (`deepwiki_mcp` → `DEEPWIKI_MCP_READ_WIKI_STRUCTURE`) to inspect open-source / CLI apps (e.g., `sherlock-project/sherlock`, verified with `log_id`).
2. **Pass 1 Research Agent (`src/research_agent.py`)**
   - Uses **Exa API** (`/search` with `type="auto"`, `objective`, and `contents={"highlights": True}`) + Composio `deepwiki_mcp` + **Gemini (`gemini-4-hydrogen`)** structured outputs into strict Pydantic enums (`src/schema.py`).
3. **Pass 2 Verification Loop (`src/verify_agent.py`)**
   - Live HTTP link auditing (`httpx`) + **Exa `/contents`** full-page extraction (`statuses`-checked) + targeted disconfirmation searches + a **Gemini Critic Agent** that audits every Pass 1 field against live primary sources and logs field-level diffs.

## Quick Start

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Copy .env.example to .env and fill in your keys:
cp .env.example .env

# 1. Verify Composio, Exa, and Gemini connections
python src/verify_setup.py

# 2. Run verified Composio session tool call
python src/composio_tools.py

# 3. Cross-reference all 100 apps against Composio's live catalog
python src/fetch_composio_catalog.py

# 4. Run Pass 1 research (pilot or full 100 apps)
python src/research_agent.py --ids 2,10,28,58,92 --out data/pilot_results.json
python src/research_agent.py --all --resume --concurrency 6

# 5. Run Pass 2 automated verification loop
python src/verify_agent.py --input data/pass1_results.json --output data/pass2_verified.json --all --resume --concurrency 5
```

## Status
- [x] Environment, skills (`composio`, `build-with-exa`), and live API verification
- [x] 100-app seed list (`data/apps.json`) & strict schema (`src/schema.py`)
- [x] Live Composio catalog match (`data/composio_catalog_match.json`)
- [x] Pass 1 & Pass 2 agents built & piloted on 5 apps
- [ ] Full 100-app Pass 1 + Pass 2 run
- [ ] Pass 3 human & browser-based accuracy audit
- [ ] Deployed single-page HTML case study
