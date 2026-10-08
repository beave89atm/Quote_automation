"""Block live Chrome, CDP, and Sectura HTTP for the whole test suite.

The guard is installed at pytest startup and reads environment variables
when a call happens, so a later ``SECTURA_CHROME_DEBUG`` still cannot
open a signed-in browser or the Sectura API.
"""

from __future__ import annotations

import os
import socket
import subprocess
import urllib.request
from urllib.parse import urlparse

import requests

_KNOWN_DEBUG_PORTS = frozenset({9222, 9223, 9224, 9333, 9230, 9231, 9234})
_DEBUG_ENV = (
    "SECTURA_CHROME_DEBUG",
    "CHROME_DEBUG_PORT",
    "SECTURA_WEB_CDP_PORT",
    "SECTURA_CHROME_DEBUG_PORT",
)
_HTTP_ENV = (
    "SECTURAFAB_BASE_URL",
    "SECTURAFAB_TOKEN_URL",
    "SECTURAFAB_WEBSITE_URL",
)
_CHROME_EXES = frozenset(
    {
        "chrome",
        "chrome.exe",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium.exe",
        "chromium-browser",
        "msedge",
        "msedge.exe",
        "microsoft-edge",
        "microsoft-edge.exe",
    }
)


class LiveSecturaBlocked(OSError):
    """A test tried to open Chrome, CDP, or the Sectura API."""


def _host_of(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    return (urlparse(raw).hostname or "").lower()


def _port_of(url: str) -> int | None:
    raw = str(url or "").strip()
    if raw.isdigit():
        return int(raw)
    if "://" not in raw:
        raw = "http://" + raw
    port = urlparse(raw).port
    return int(port) if port else None


def _configured_debug_targets() -> list[tuple[str, int | None]]:
    found: list[tuple[str, int | None]] = []
    for key in _DEBUG_ENV:
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        if raw.isdigit():
            found.append(("127.0.0.1", int(raw)))
            continue
        found.append((_host_of(raw) or "127.0.0.1", _port_of(raw)))
    return found


def _configured_http_hosts() -> set[str]:
    hosts: set[str] = set()
    for key in _HTTP_ENV:
        host = _host_of(os.environ.get(key) or "")
        if host and "redacted" not in host:
            hosts.add(host)
    try:
        from secturafab.config import SecturaFabConfig

        cfg = SecturaFabConfig.from_env(env_file=None)
        for url in (cfg.base_url, cfg.token_url, cfg.website_root):
            host = _host_of(url)
            if host and "redacted" not in host:
                hosts.add(host)
    except Exception:
        pass
    return hosts


def _debug_ports() -> set[int]:
    ports = set(_KNOWN_DEBUG_PORTS)
    for _host, port in _configured_debug_targets():
        if port:
            ports.add(port)
    return ports


def _is_cdp_path(path: str) -> bool:
    raw = str(path or "")
    if raw == "/json" or raw.startswith("/json/") or raw.startswith("/json?"):
        return True
    return False


def _sectura_host(host: str) -> bool:
    folded = str(host or "").lower()
    if not folded:
        return False
    if "sectura" in folded:
        return True
    return folded in _configured_http_hosts()


def _refuse_url(url: str) -> None:
    raw = str(url or "")
    parsed = urlparse(raw if "://" in raw else "http://" + raw)
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    port = parsed.port
    if parsed.scheme in {"ws", "wss"} or _is_cdp_path(path):
        raise LiveSecturaBlocked(f"blocked CDP URL during tests ({host}:{port}{path})")
    if port in _debug_ports():
        raise LiveSecturaBlocked(f"blocked debug port during tests ({host}:{port})")
    for cfg_host, cfg_port in _configured_debug_targets():
        if host == cfg_host and (cfg_port is None or port == cfg_port):
            raise LiveSecturaBlocked(
                f"blocked configured CDP endpoint during tests ({host}:{port})"
            )
    if _sectura_host(host):
        raise LiveSecturaBlocked(f"blocked Sectura HTTP during tests ({host})")


def _address_host_port(address) -> tuple[str, int | None]:
    if isinstance(address, tuple) and address:
        host = str(address[0] or "")
        port = address[1] if len(address) > 1 else None
        try:
            port_i = int(port) if port is not None else None
        except (TypeError, ValueError):
            port_i = None
        return host, port_i
    return "", None


def _refuse_address(address) -> None:
    host, port = _address_host_port(address)
    folded = host.lower()
    if port in _debug_ports():
        raise LiveSecturaBlocked(f"blocked debug socket during tests ({folded}:{port})")
    for cfg_host, cfg_port in _configured_debug_targets():
        if folded == cfg_host and cfg_port and port == cfg_port:
            raise LiveSecturaBlocked(
                f"blocked configured CDP socket during tests ({folded}:{port})"
            )
    if _sectura_host(folded):
        raise LiveSecturaBlocked(f"blocked Sectura socket during tests ({folded})")


def _chrome_launch(args) -> bool:
    if isinstance(args, (str, bytes)):
        text = args.decode() if isinstance(args, bytes) else args
        parts = text.split()
    else:
        try:
            parts = [str(part) for part in args]
        except TypeError:
            return False
    if not parts:
        return False
    blob = " ".join(parts).lower()
    if "--remote-debugging-port" in blob or "--remote-debugging-pipe" in blob:
        return True
    name = parts[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in _CHROME_EXES


def install() -> None:
    """Install the blockers once. Safe to call again."""
    if getattr(urllib.request.urlopen, "_sectura_guard", False):
        return

    orig_urlopen = urllib.request.urlopen
    orig_create = socket.create_connection
    orig_connect = socket.socket.connect
    orig_popen = subprocess.Popen
    orig_request = requests.Session.request

    def guarded_urlopen(url, *args, **kwargs):
        target = url.full_url if isinstance(url, urllib.request.Request) else str(url)
        _refuse_url(target)
        return orig_urlopen(url, *args, **kwargs)

    def guarded_create(address, *args, **kwargs):
        _refuse_address(address)
        return orig_create(address, *args, **kwargs)

    def guarded_connect(self, address):
        _refuse_address(address)
        return orig_connect(self, address)

    def guarded_popen(args, *popenargs, **kwargs):
        if _chrome_launch(args):
            raise LiveSecturaBlocked("blocked Chrome launch during tests")
        return orig_popen(args, *popenargs, **kwargs)

    def guarded_session_request(self, method, url, *args, **kwargs):
        _refuse_url(str(url))
        return orig_request(self, method, url, *args, **kwargs)

    guarded_urlopen._sectura_guard = True  # type: ignore[attr-defined]
    guarded_create._sectura_guard = True  # type: ignore[attr-defined]
    urllib.request.urlopen = guarded_urlopen
    socket.create_connection = guarded_create
    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    subprocess.Popen = guarded_popen  # type: ignore[assignment]
    requests.Session.request = guarded_session_request  # type: ignore[method-assign]
