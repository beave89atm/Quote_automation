from __future__ import annotations

import argparse
import json
import sys

from .client import SecturaFabClient, ping_token_endpoint
from .config import SecturaFabConfig
from .discover import write_discovery_report
from .quotes import QuoteService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m secturafab",
        description="SecturaFAB API utilities for quote automation",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth-check", help="Validate OAuth username/password login")

    discover = sub.add_parser(
        "discover",
        help="Authenticate and probe common API routes; write .discovery report",
    )
    discover.add_argument(
        "--out",
        default=".discovery",
        help="Output directory for discovery artifacts (default: .discovery)",
    )

    who = sub.add_parser("whoami", help="Fetch current user info if available")
    _ = who

    sub.add_parser(
        "website-auth-check",
        help="Probe www MVC Finish auth (GetItem_AddView) — no quote writes",
    )

    quotes = sub.add_parser("list-quotes", help="List quotes via adaptive paths")
    quotes.add_argument("--top", type=int, default=25)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = SecturaFabConfig.from_env()

    if args.command == "auth-check":
        result = ping_token_endpoint(config)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    client = SecturaFabClient(config)

    if args.command == "discover":
        path = write_discovery_report(client, output_dir=args.out)
        print(f"Wrote discovery report to {path}")
        report = json.loads(path.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "openapi_found": report["openapi_found"],
                    "successful": report["successful"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "whoami":
        print(json.dumps(client.whoami(), indent=2, default=str))
        return 0

    if args.command == "website-auth-check":
        result = client.probe_website_finish_auth()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("can_finish") else 1

    if args.command == "list-quotes":
        data = QuoteService(client).list_quotes(top=args.top)
        print(json.dumps(data, indent=2, default=str))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
