"""
Upgrades 2 & 3 helper: Check Composio connection status for `github` and `exa`
for `user_id="product_ops_researcher"`, and generate Composio Connect Links
via `session.authorize()` for any toolkit not yet connected.
"""
from __future__ import annotations

import argparse
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

DEFAULT_USER_ID = "product_ops_researcher"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check or generate Composio Connect Links")
    parser.add_argument(
        "--toolkits",
        type=str,
        default="github,exa",
        help="Comma-separated Composio toolkit slugs to check/authorize",
    )
    args = parser.parse_args()
    slugs = [s.strip() for s in args.toolkits.split(",") if s.strip()]

    composio = Composio()
    session = composio.create(user_id=DEFAULT_USER_ID, toolkits=slugs)
    print(f"Session ID: {session.session_id} | User ID: {DEFAULT_USER_ID}\n")

    status_page = session.toolkits(toolkits=slugs)
    active_map: dict[str, bool] = {}
    for item in status_page.items:
        conn = getattr(item, "connection", None)
        active_map[item.slug] = bool(getattr(conn, "is_active", False))

    for slug in slugs:
        if active_map.get(slug):
            print(f"[CONNECTED] {slug}")
        else:
            try:
                req = session.authorize(slug)
                url = getattr(req, "redirect_url", None)
                conn_id = getattr(req, "id", None)
                print(f"[ACTION NEEDED] {slug} -> Open Connect Link to authorize:")
                print(f"  Connect Link: {url}")
                print(f"  Connection Request ID: {conn_id}\n")
            except Exception as e:
                print(f"[ERROR] {slug}: {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
