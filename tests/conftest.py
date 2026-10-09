"""Keep pytest off live Chrome DevTools and SecturaFAB.

``secturafab/chrome_cdp.py`` probes local debug ports (9222, 9223, 9224, 9333)
with ``urllib`` and opens CDP websockets. This process has no network allow-list
of its own, so the guard is installed before tests run. Blocked lookups fail
immediately and never open a socket.
"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

_DEFAULT_CDP_PORTS = frozenset({9222, 9223, 9224, 9333})
_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "0.0.0.0", "::"})

_real_getaddrinfo = socket.getaddrinfo
_real_connect = socket.socket.connect


def _host_text(host: object) -> str:
    if host is None:
        return ""
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    text = str(host).strip().lower().rstrip(".")
    if text.startswith("[") and "]" in text:
        text = text[1 : text.index("]")]
    if text.startswith("::ffff:"):
        text = text.removeprefix("::ffff:")
    return text


def _port_number(port: object) -> int | None:
    if port is None or port == "":
        return None
    try:
        return int(port)
    except (TypeError, ValueError):
        return None


def _env_cdp_ports() -> set[int]:
    ports: set[int] = set()
    for key in ("SECTURA_WEB_CDP_PORT", "CHROME_DEBUG_PORT", "SECTURA_CHROME_DEBUG"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        if raw.isdigit():
            ports.add(int(raw))
            continue
        parsed = urlparse(raw if "://" in raw else f"//{raw}")
        if parsed.port:
            ports.add(int(parsed.port))
    return ports


def blocked_live_reason(host: object, port: object) -> str | None:
    """Why this target must not be contacted, or None when it is allowed."""
    name = _host_text(host)
    number = _port_number(port)
    if name == "secturafab.com" or name.endswith(".secturafab.com"):
        return "SecturaFAB"
    if number in _DEFAULT_CDP_PORTS:
        return "Chrome DevTools"
    if name in _LOCAL_HOSTS and number in _env_cdp_ports():
        return "Chrome DevTools"
    return None


def _guard_getaddrinfo(host, port, *args, **kwargs):
    reason = blocked_live_reason(host, port)
    if reason:
        raise socket.gaierror(socket.EAI_NONAME, f"tests must not reach live {reason}")
    return _real_getaddrinfo(host, port, *args, **kwargs)


def _address_host_port(address: object) -> tuple[object, object]:
    if isinstance(address, tuple) and len(address) >= 2:
        return address[0], address[1]
    return None, None


def _guard_connect(self, address):
    host, port = _address_host_port(address)
    reason = blocked_live_reason(host, port)
    if reason:
        raise OSError(f"tests must not reach live {reason}")
    return _real_connect(self, address)


def install_live_network_guard() -> None:
    socket.getaddrinfo = _guard_getaddrinfo
    socket.socket.connect = _guard_connect


install_live_network_guard()
