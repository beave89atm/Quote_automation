"""The suite must refuse a real browser, CDP socket, and Sectura HTTP call."""

from __future__ import annotations

import socket
import subprocess
import urllib.error
import urllib.request

import pytest
import requests

from secturafab.chrome_cdp import _http_json, _ws_handshake, chrome_debug_bases
from secturafab.web_login import launch_chrome_incognito
from tests.live_network_guard import LiveSecturaBlocked


def test_suite_blocks_cdp_chrome_and_sectura_http(monkeypatch):
    monkeypatch.setenv("SECTURA_CHROME_DEBUG", "http://10.9.8.7:4444")
    monkeypatch.setenv("SECTURAFAB_BASE_URL", "https://api.example.sectura.test")
    monkeypatch.setenv("SECTURAFAB_TOKEN_URL", "https://token.example.sectura.test/token")

    with pytest.raises(LiveSecturaBlocked):
        urllib.request.urlopen("http://127.0.0.1:9224/json/version", timeout=0.2)
    with pytest.raises(LiveSecturaBlocked):
        urllib.request.urlopen("http://10.9.8.7:4444/json/version", timeout=0.2)
    with pytest.raises(LiveSecturaBlocked):
        urllib.request.urlopen(
            "https://www.secturafab.com/api/v2/organization/lookup", timeout=0.2
        )
    with pytest.raises(LiveSecturaBlocked):
        _http_json("http://127.0.0.1:9224/json/version")
    with pytest.raises(LiveSecturaBlocked):
        socket.create_connection(("127.0.0.1", 9224), timeout=0.2)
    with pytest.raises(LiveSecturaBlocked):
        socket.create_connection(("10.9.8.7", 4444), timeout=0.2)
    with pytest.raises(LiveSecturaBlocked):
        _ws_handshake("ws://127.0.0.1:9224/devtools/page/ABC")
    with pytest.raises(LiveSecturaBlocked):
        subprocess.Popen(["google-chrome", "--remote-debugging-port=9224"])
    with pytest.raises(LiveSecturaBlocked):
        launch_chrome_incognito(port=9224)
    with pytest.raises(LiveSecturaBlocked):
        requests.get("https://www.secturafab.com/api/v2/test", timeout=0.2)

    monkeypatch.setenv("SECTURA_CHROME_DEBUG", "http://127.0.0.1:9224")
    assert chrome_debug_bases() == []

    with pytest.raises(OSError) as refused:
        urllib.request.urlopen("http://127.0.0.1:9/health", timeout=0.2)
    assert not isinstance(refused.value, LiveSecturaBlocked)
    assert isinstance(refused.value, urllib.error.URLError)
