from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .client import SecturaFabClient


# Common ASP.NET Web API controller names used by fabrication quoting apps.
DEFAULT_PROBE_PATHS = [
    "docs/v1",
    "swagger/docs/v1",
    "Help",
    "Account/UserInfo",
    "Account/Me",
    "Users/Me",
    "Quotes",
    "Quote",
    "quotes",
    "Customers",
    "Customer",
    "customers",
    "Contacts",
    "Vendors",
    "Products",
    "Materials",
    "Inventory",
    "Operations",
    "Locations",
    "Companies",
    "Organization",
    "Tenants",
]


@dataclass
class ProbeResult:
    path: str
    status_code: int
    content_type: str
    ok: bool
    preview: str


def probe_endpoints(
    client: SecturaFabClient,
    paths: list[str] | None = None,
) -> list[ProbeResult]:
    """Hit a list of relative /api paths and return status summaries."""
    results: list[ProbeResult] = []
    for path in paths or DEFAULT_PROBE_PATHS:
        response = client.request("GET", path)
        content_type = response.headers.get("content-type", "")
        preview = response.text[:240].replace("\n", " ")
        results.append(
            ProbeResult(
                path=path,
                status_code=response.status_code,
                content_type=content_type,
                ok=response.status_code < 400,
                preview=preview,
            )
        )
    return results


def try_fetch_openapi(client: SecturaFabClient) -> dict[str, Any] | None:
    """Attempt to download OpenAPI/Swagger JSON after authentication."""
    relative_candidates = [
        "docs/v1",
        "swagger/docs/v1",
    ]
    absolute_candidates = [
        f"{client.config.base_url}/swagger/docs/v1",
        f"{client.config.base_url}/api/docs/v1",
    ]

    requests_to_try: list[tuple[str, bool]] = [
        *((path, False) for path in relative_candidates),
        *((path, True) for path in absolute_candidates),
    ]

    for path, absolute in requests_to_try:
        response = client.request(
            "GET",
            path,
            headers={"Accept": "application/json"},
            allow_absolute=absolute,
            retry_on_auth_error=False,
        )
        if response.status_code >= 400:
            continue
        try:
            payload = response.json()
        except ValueError:
            continue
        if isinstance(payload, dict) and (
            "swagger" in payload or "openapi" in payload or "paths" in payload
        ):
            return payload
        # Swagger UI resource listing sometimes nests apis.
        if isinstance(payload, dict) and "apis" in payload:
            return payload
    return None


def write_discovery_report(
    client: SecturaFabClient,
    output_dir: str | Path = ".discovery",
) -> Path:
    """Authenticate, probe endpoints, and write a local discovery report."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    token = client.authenticate()
    token_summary = {
        "token_type": token.token_type,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "raw_keys": sorted((token.raw or {}).keys()),
    }
    (out / "token_summary.json").write_text(
        json.dumps(token_summary, indent=2) + "\n", encoding="utf-8"
    )

    openapi = try_fetch_openapi(client)
    if openapi is not None:
        (out / "openapi.json").write_text(
            json.dumps(openapi, indent=2) + "\n", encoding="utf-8"
        )

    probes = probe_endpoints(client)
    report = {
        "base_url": client.config.base_url,
        "api_root": client.config.api_root,
        "openapi_found": openapi is not None,
        "probes": [asdict(item) for item in probes],
        "successful": [asdict(item) for item in probes if item.ok],
    }
    report_path = out / "api_probe_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report_path
