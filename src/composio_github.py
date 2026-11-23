"""
Upgrade 2: Live GitHub MCP & Open-Source Repo Auditor via Composio `github` toolkit.

Uses Composio Platform Session runtime discovery (`session.search()`) to locate
the repo-inspection tool slug dynamically (never hardcoding/guessing slugs) and
executes it to verify whether a cited GitHub repo is:
- Owned by the official vendor org vs. a third-party/community author
- Actively maintained (last push date, archived flag)
- Popular / credible (stargazers_count)

Logs every call's Composio `log_id` for the verification audit trail.
"""
from __future__ import annotations

import re
from typing import Any

GITHUB_URL_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


class ComposioGitHubAuditor:
    def __init__(self, session: Any) -> None:
        self.session = session
        self.enabled = False
        self.repo_tool_slug: str | None = None
        self.owner_param: str = "owner"
        self.repo_param: str = "repo"
        self._init_tool()

    def _init_tool(self) -> None:
        try:
            tk_status = self.session.toolkits(toolkits=["github"])
            items = getattr(tk_status, "items", []) or []
            is_active = any(
                getattr(getattr(i, "connection", None), "is_active", False)
                for i in items
                if getattr(i, "slug", "") == "github"
            )
            if not is_active:
                self.enabled = False
                return

            # Runtime tool discovery via session.search()
            sr = self.session.search(query="get github repository metadata details by owner and repo name")
            dump = sr.model_dump(mode="json")
            slugs: list[str] = []
            for r in dump.get("results", []):
                slugs.extend(r.get("primary_tool_slugs", []))
            schemas = dump.get("tool_schemas", {})

            chosen = None
            for s in slugs:
                if "GET_A_REPOSITORY" in s.upper() or "GET_REPO" in s.upper():
                    chosen = s
                    break
            if not chosen and slugs:
                chosen = slugs[0]

            if chosen:
                self.repo_tool_slug = chosen
                props = (schemas.get(chosen, {}).get("input_schema") or {}).get("properties", {})
                if "owner" in props:
                    self.owner_param = "owner"
                if "repo" in props:
                    self.repo_param = "repo"
                self.enabled = True
        except Exception:
            self.enabled = False

    def extract_github_repo(self, urls: list[str]) -> tuple[str, str] | None:
        for u in urls:
            if not u:
                continue
            m = GITHUB_URL_RE.search(u)
            if m:
                owner, repo = m.group(1), m.group(2)
                repo = repo.removesuffix(".git").split("#")[0].split("?")[0]
                if owner.lower() not in ("topics", "search", "orgs", "marketplace"):
                    return owner, repo
        return None

    def audit_repo(self, owner: str, repo: str) -> dict[str, Any] | None:
        if not self.enabled or not self.repo_tool_slug:
            return None
        try:
            res = self.session.execute(
                self.repo_tool_slug,
                arguments={self.owner_param: owner, self.repo_param: repo},
            )
            dump = res.model_dump(mode="json")
            data = dump.get("data") or {}
            # Some GitHub responses nest payload under 'data' or return top-level fields
            repo_obj = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else data
            if not isinstance(repo_obj, dict):
                repo_obj = {}
            owner_obj = repo_obj.get("owner") if isinstance(repo_obj.get("owner"), dict) else {}
            return {
                "repo": f"{owner}/{repo}",
                "owner_login": owner_obj.get("login", owner),
                "owner_type": owner_obj.get("type"),  # "Organization" vs "User"
                "stars": repo_obj.get("stargazers_count"),
                "archived": repo_obj.get("archived"),
                "pushed_at": repo_obj.get("pushed_at"),
                "license": (repo_obj.get("license") or {}).get("spdx_id") if isinstance(repo_obj.get("license"), dict) else None,
                "description": (repo_obj.get("description") or "")[:200],
                "tool_slug": self.repo_tool_slug,
                "composio_log_id": res.log_id,
                "result_type": res.result_type,
            }
        except Exception as e:
            return {"repo": f"{owner}/{repo}", "error": f"{type(e).__name__}: {e}"}
