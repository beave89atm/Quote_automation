"""Client retries for transient SecturaFAB/Cloudflare errors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from secturafab.client import SecturaFabApiError, SecturaFabClient


def test_get_json_retries_502_then_succeeds():
    client = SecturaFabClient.__new__(SecturaFabClient)
    bad = MagicMock()
    bad.status_code = 502
    bad.url = "https://api.secturafab.com/api/v1/quote/x"
    bad.content = b"{}"
    bad.text = "bad gateway"
    bad.json.side_effect = ValueError("no json")
    good = MagicMock()
    good.status_code = 200
    good.url = bad.url
    good.content = b'{"ItemCount": 2}'
    good.json.return_value = {"ItemCount": 2}

    with patch.object(client, "request", side_effect=[bad, good]) as req, patch(
        "time.sleep"
    ):
        data = client.get_json("v1/quote/x", retries=3)

    assert data["ItemCount"] == 2
    assert req.call_count == 2


def test_get_json_exhausted_502_raises():
    client = SecturaFabClient.__new__(SecturaFabClient)
    bad = MagicMock()
    bad.status_code = 502
    bad.url = "https://api.secturafab.com/api/v1/quote/x"
    bad.content = b""
    bad.text = "bad gateway"
    bad.json.side_effect = ValueError("no json")

    with patch.object(client, "request", return_value=bad), patch("time.sleep"):
        with pytest.raises(SecturaFabApiError) as exc:
            client.get_json("v1/quote/x", retries=2)
    assert exc.value.status_code == 502
