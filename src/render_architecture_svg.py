"""
Upgrade 4: Validate and render the 3-Pass Research & Verification Pipeline
Architecture Diagram using Composio's live `mermaid_chart_mcp` toolkit.

Records the live Composio `session_id` and `log_id` into `data/mermaid_architecture.json`.
"""
from __future__ import annotations

import json
from pathlib import Path
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "data" / "mermaid_architecture.json"
OUT_MMD = ROOT / "assets" / "architecture.mmd"

DIAGRAM_CODE = """flowchart LR
    Seed["100 Target Apps<br/>(10 Categories)"] --> P1

    subgraph P1["Pass 1: Broad Research Agent"]
        Exa1["Exa /search<br/>(Docs, Auth, Gating, MCP)"]
        DW["Composio Session:<br/>deepwiki_mcp"]
        Gem1["Gemini 4 Hydrogen<br/>(Strict Pydantic JSON)"]
        Exa1 --> Gem1
        DW --> Gem1
    end

    Gem1 --> Snap1[("pass1_results.json<br/>Immutable Baseline")]
    Snap1 --> P2

    subgraph P2["Pass 2: Automated Verification Loop"]
        URL["HTTP Link Health<br/>(404 vs Bot-Shield)"]
        Exa2["Exa /contents +<br/>Disconfirmation /search"]
        Cat["Composio v3.1 Live Catalog<br/>(1,842 Toolkits Ground Truth)"]
        GH["Composio Session:<br/>github Toolkit (MCP Repo Audit)"]
        Critic["Gemini Critic Agent<br/>(Field-Level Diff Audit)"]
        URL --> Critic
        Exa2 --> Critic
        Cat --> Critic
        GH --> Critic
    end

    Critic --> Snap2[("pass2_verified.json +<br/>verification_diff_report.json")]
    Snap2 --> P3

    subgraph P3["Pass 3: Human + Browser Audit"]
        Sample["Stratified 20-25 App<br/>Manual & Browser Check"]
        Metrics["Accuracy Delta:<br/>Pass 1 -> Pass 2 -> Final"]
        Sample --> Metrics
    end

    Metrics --> Out["Interactive HTML Case Study<br/>+ Agent-Ready JSON Export"]
"""


def main() -> None:
    composio = Composio()
    session = composio.create(
        user_id="product_ops_researcher",
        toolkits=["mermaid_chart_mcp"],
    )
    res = session.execute(
        "MERMAID_CHART_MCP_VALIDATE_AND_RENDER_MERMAID_DIAGRAM",
        arguments={
            "title": "Composio 100-App Research & Verification Pipeline",
            "diagramCode": DIAGRAM_CODE,
        },
    )
    dump = res.model_dump(mode="json")

    OUT_MMD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MMD.write_text(DIAGRAM_CODE, encoding="utf-8")

    payload = {
        "session_id": session.session_id,
        "user_id": "product_ops_researcher",
        "toolkit": "mermaid_chart_mcp",
        "tool_slug": "MERMAID_CHART_MCP_VALIDATE_AND_RENDER_MERMAID_DIAGRAM",
        "result_type": res.result_type,
        "log_id": res.log_id,
        "error": res.error,
        "diagram_code": DIAGRAM_CODE,
        "response_data": dump.get("data"),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Session ID: {session.session_id}")
    print(f"Result type: {res.result_type} | Log ID: {res.log_id}")
    print(f"Response preview: {str(dump.get('data'))[:600]}")


if __name__ == "__main__":
    main()
