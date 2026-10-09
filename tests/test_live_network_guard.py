"""Pytest must not open a live Chrome DevTools or SecturaFAB connection."""

from __future__ import annotations

import socket

import pytest

from tests.conftest import blocked_live_reason


def test_blocked_targets() -> None:
    assert blocked_live_reason("127.0.0.1", 9224) == "Chrome DevTools"
    assert blocked_live_reason("localhost", "9222") == "Chrome DevTools"
    assert blocked_live_reason("::1", 9333) == "Chrome DevTools"
    assert blocked_live_reason("www.secturafab.com", 443) == "SecturaFAB"
    assert blocked_live_reason("api.secturafab.com", 443) == "SecturaFAB"
    assert blocked_live_reason("127.0.0.1", 8000) is None
    assert blocked_live_reason("example.test", 443) is None


def test_cdp_lookup_fails_before_connect() -> None:
    with pytest.raises(socket.gaierror, match="Chrome DevTools"):
        socket.getaddrinfo("127.0.0.1", 9224)


def test_secturafab_lookup_fails_before_connect() -> None:
    with pytest.raises(socket.gaierror, match="SecturaFAB"):
        socket.getaddrinfo("www.secturafab.com", 443)


def test_chrome_debug_probe_returns_empty() -> None:
    from secturafab.chrome_cdp import chrome_debug_bases

    assert chrome_debug_bases() == []


def test_direct_cdp_connect_is_refused() -> None:
    sock = socket.socket()
    try:
        with pytest.raises(OSError, match="Chrome DevTools"):
            sock.connect(("127.0.0.1", 9224))
    finally:
        sock.close()
