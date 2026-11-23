from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


AuthMethod = Literal[
    "OAuth2",
    "API Key",
    "Bearer Token",
    "Basic Auth",
    "JWT",
    "HMAC / Signature",
    "App Token / Bot Token",
    "CLI / Local Only",
    "No Auth / Open",
    "Other",
]

AccessModel = Literal[
    "Self-Serve Free / Trial",
    "Self-Serve Paid Plan",
    "Self-Serve Dev + App Review",
    "Admin / Customer Account Required",
    "Partner / Sales-Gated",
    "Open-Source / Local Tool",
]

ApiProtocol = Literal[
    "REST",
    "GraphQL",
    "REST + GraphQL",
    "RPC / Proprietary SDK",
    "MCP Only",
    "CLI / Local Only",
    "No Public API",
]

ApiBreadth = Literal[
    "Broad (Full Platform)",
    "Medium (Core Workflows)",
    "Narrow (Single-Purpose / Limited)",
    "N/A",
]

McpStatus = Literal[
    "Official MCP",
    "Community MCP Only",
    "None Found",
]

BuildabilityVerdict = Literal[
    "Ready Today (Easy Win)",
    "Buildable with Friction",
    "Gated / Needs Outreach",
    "Blocked / Not API-Native",
]

ConfidenceLevel = Literal["High", "Medium", "Low"]


class AppSeed(BaseModel):
    id: int
    category: str
    name: str
    hint: str


class AppResearchRecord(BaseModel):
    id: int
    name: str
    category: str
    hint: str
    one_liner: str = Field(description="What the app does in one crisp sentence.")
    auth_methods: list[AuthMethod] = Field(
        description="Primary authentication method(s) supported by the API."
    )
    auth_notes: str = Field(
        description="Concise nuance on auth (e.g., OAuth2 PKCE, refresh tokens, scoped API keys, Basic over API key)."
    )
    access_model: AccessModel = Field(
        description="Whether a developer can get working API credentials self-serve or hits a paywall/review/partner gate."
    )
    access_notes: str = Field(
        description="Specific details on sandbox/trial, paid tier requirement, app review, or partner/sales gate."
    )
    api_protocol: ApiProtocol = Field(
        description="Primary API protocol(s) exposed publicly."
    )
    api_breadth: ApiBreadth = Field(
        description="How broad the documented public API surface is."
    )
    api_surface_notes: str = Field(
        description="Summary of key resources/endpoints, rate limits or notable gaps."
    )
    mcp_status: McpStatus = Field(
        description="Whether an official vendor MCP server or community MCP exists."
    )
    mcp_evidence_url: str | None = Field(
        default=None,
        description="Direct URL to official or notable community MCP docs/repo, or null if none found.",
    )
    openapi_spec_available: Literal["Yes", "No", "Unknown"] = Field(
        description="Whether a public OpenAPI / Swagger / GraphQL schema is available."
    )
    webhooks_supported: Literal["Yes", "No", "Unknown"] = Field(
        description="Whether webhooks or event triggers are documented."
    )
    buildability_verdict: BuildabilityVerdict = Field(
        description="Could Composio ship this as an agent toolkit today?"
    )
    primary_blocker: str = Field(
        description="Main blocker or friction point, or 'None' if Ready Today."
    )
    evidence_urls: list[str] = Field(
        min_length=1,
        description="Direct official docs / GitHub / pricing / developer portal URLs backing the answers.",
    )
    confidence: ConfidenceLevel = Field(
        description="Self-assessed confidence based on direct primary-source evidence."
    )
    # Enriched programmatically (not from LLM)
    composio_catalog_slugs: list[str] = Field(
        default_factory=list,
        description="Matching toolkit slugs discovered live from Composio's catalog.",
    )
    url_health: dict[str, int | str] = Field(
        default_factory=dict,
        description="HTTP status code or error for each evidence URL.",
    )
    verification_changes: list[str] = Field(
        default_factory=list,
        description="Audit log of fields modified during automated verification or human review.",
    )
    human_audited: bool = Field(
        default=False,
        description="Whether a human manually verified this record against live docs.",
    )
