"""Mocked CDP coverage for one-shot Sectura Incognito sign-in."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from secturafab.web_login import (
    LOGIN_URL,
    SecturaReloginError,
    attempt_sectura_relogin,
    chrome_incognito_command,
    chrome_launch_env,
    reset_relogin_attempt_for_tests,
)

SECRET = "s3cret-value-should-not-leak"
EMAIL = "person@example.test"


class FakeCdp:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.up = mode != "relaunch"
        self.probes = 0
        self.filled = False
        self.saw_remember = False
        self.used_file_secret = False
        self.used_other_email = False
        self.navigated = ""

    def reachable(self, port: int) -> bool:
        return self.up

    def pages(self, port: int) -> list[dict]:
        return [
            {
                "type": "page",
                "url": LOGIN_URL,
                "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/1",
            }
        ]

    def navigate(self, ws_url: str, url: str) -> None:
        self.navigated = url

    def evaluate(self, ws_url: str, expression: str) -> dict:
        if expression.startswith("(function(creds)"):
            self.filled = True
            self.saw_remember = "remember" in expression and "node.click()" in expression
            self.used_file_secret = SECRET in expression and EMAIL in expression
            self.used_other_email = "other@example.test" in expression
            return {"ok": True, "state": "submitted"}
        self.probes += 1
        login = {
            "url": "https://www.secturafab.com/Account/Login",
            "title": "SecturaFAB-Login",
            "license": False,
            "verification": False,
            "login_error": False,
            "on_login": True,
            "on_quote": False,
        }
        if self.mode == "verification" and self.probes > 1:
            return {
                "url": "https://www.secturafab.com/Account/VerifyCode",
                "title": "Verify",
                "license": False,
                "verification": True,
                "login_error": False,
                "on_login": False,
                "on_quote": False,
            }
        if self.mode in {"success", "relaunch"} and self.probes > 1:
            return {
                "url": "https://www.secturafab.com/Quote",
                "title": "Quotes",
                "license": False,
                "verification": False,
                "login_error": False,
                "on_login": False,
                "on_quote": True,
            }
        return login


@pytest.fixture(autouse=True)
def _fresh_attempt():
    reset_relogin_attempt_for_tests()
    yield
    reset_relogin_attempt_for_tests()


def _dirs(tmp_path):
    alerts = tmp_path / "alerts"
    locks = tmp_path / "locks"
    return alerts, locks


def _env() -> dict[str, str]:
    return {"SECTURA_WEB_EMAIL": EMAIL, "SECTURA_WEB_PASSWORD": SECRET}


def _assert_secret_hidden(text: str) -> None:
    assert SECRET not in text
    assert EMAIL not in text


def test_relogin_success_lands_on_quote(tmp_path):
    alerts, locks = _dirs(tmp_path)
    cdp = FakeCdp("success")
    notes: list[str] = []
    attempt_sectura_relogin(
        trigger="login_url",
        cdp=cdp,
        launcher=lambda **kwargs: (_ for _ in ()).throw(AssertionError("launched")),
        on_alert=notes.append,
        alerts=alerts,
        locks=locks,
        env=_env(),
        sleep=lambda _s: None,
        max_polls=2,
        port=9224,
    )
    assert cdp.filled is True
    assert cdp.saw_remember is True
    assert notes == []
    assert list(locks.glob("relogin-*.txt"))
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="login_url",
            cdp=cdp,
            alerts=alerts,
            locks=locks,
            env=_env(),
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "relogin_already_attempted"
    _assert_secret_hidden(str(raised.value))


def _write_secrets(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_relogin_env_credentials_win_over_secrets_file(tmp_path):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    secrets.write_text("{", encoding="utf-8")
    cdp = FakeCdp("success")
    attempt_sectura_relogin(
        trigger="login_url",
        cdp=cdp,
        launcher=lambda **kwargs: (_ for _ in ()).throw(AssertionError("launched")),
        alerts=alerts,
        locks=locks,
        env=_env(),
        secrets_file=secrets,
        sleep=lambda _s: None,
        max_polls=2,
        port=9224,
    )
    assert cdp.filled is True
    assert cdp.used_file_secret is True
    assert list(alerts.glob("alert-*.txt")) == []
    command = " ".join(chrome_incognito_command(9224))
    _assert_secret_hidden(command)


@pytest.mark.parametrize(
    "payload",
    [
        {"card": {"SECTURA_WEB_EMAIL": EMAIL, "SECTURA_WEB_PASSWORD": SECRET}},
        {"card.SECTURA_WEB_EMAIL": EMAIL, "card.SECTURA_WEB_PASSWORD": SECRET},
    ],
)
def test_relogin_secrets_file_fallback(tmp_path, payload):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    _write_secrets(secrets, payload)
    cdp = FakeCdp("success")
    launched: list[dict] = []
    attempt_sectura_relogin(
        trigger="no_sectura_tab",
        cdp=cdp,
        launcher=lambda **kwargs: launched.append(kwargs),
        alerts=alerts,
        locks=locks,
        env={},
        secrets_file=secrets,
        sleep=lambda _s: None,
        max_polls=2,
        port=9224,
    )
    assert cdp.filled is True
    assert cdp.used_file_secret is True
    assert launched == []
    assert list(alerts.glob("alert-*.txt")) == []
    _assert_secret_hidden(" ".join(chrome_incognito_command(9224)))


def test_relogin_env_email_uses_file_password(tmp_path):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    _write_secrets(
        secrets,
        {
            "card": {
                "SECTURA_WEB_EMAIL": "other@example.test",
                "SECTURA_WEB_PASSWORD": SECRET,
            }
        },
    )
    cdp = FakeCdp("success")
    attempt_sectura_relogin(
        trigger="login_url",
        cdp=cdp,
        alerts=alerts,
        locks=locks,
        env={"SECTURA_WEB_EMAIL": EMAIL},
        secrets_file=secrets,
        sleep=lambda _s: None,
        max_polls=2,
        port=9224,
    )
    assert cdp.used_file_secret is True
    assert cdp.used_other_email is False


def test_relogin_credentials_missing_from_env_and_file(tmp_path, monkeypatch):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    _write_secrets(secrets, {"card": {}})
    monkeypatch.setenv("SECTURA_WEB_PASSWORD", SECRET)
    launched = []
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="no_sectura_tab",
            launcher=lambda **kwargs: launched.append(kwargs),
            alerts=alerts,
            locks=locks,
            env={},
            secrets_file=secrets,
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "credentials_missing"
    assert launched == []
    text = (alerts / next(alerts.iterdir()).name).read_text(encoding="utf-8")
    assert "Chief of Staff" in text
    assert "credentials_missing" in text
    _assert_secret_hidden(text)
    _assert_secret_hidden(str(raised.value))


def test_relogin_missing_secrets_file_alerts_without_chrome(tmp_path, monkeypatch):
    alerts, locks = _dirs(tmp_path)
    monkeypatch.delenv("SECTURA_WEB_EMAIL", raising=False)
    monkeypatch.delenv("SECTURA_WEB_PASSWORD", raising=False)
    monkeypatch.setenv("SECTURA_WEB_PASSWORD", SECRET)
    launched = []
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="no_sectura_tab",
            launcher=lambda **kwargs: launched.append(kwargs),
            alerts=alerts,
            locks=locks,
            env={},
            secrets_file=tmp_path / "absent.json",
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "secrets_file_missing"
    assert launched == []
    text = (alerts / next(alerts.iterdir()).name).read_text(encoding="utf-8")
    assert "Chief of Staff" in text
    assert "secrets_file_missing" in text
    assert str(tmp_path) not in text
    _assert_secret_hidden(text)
    _assert_secret_hidden(str(raised.value))


def test_relogin_unreadable_secrets_file(tmp_path, monkeypatch):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    _write_secrets(secrets, {"card": {"SECTURA_WEB_EMAIL": EMAIL, "SECTURA_WEB_PASSWORD": SECRET}})
    original = Path.read_text

    def _deny(self, *args, **kwargs):
        if self == secrets:
            raise PermissionError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _deny)
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="login_url",
            alerts=alerts,
            locks=locks,
            env={},
            secrets_file=secrets,
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "secrets_file_unreadable"
    text = "".join(path.read_text(encoding="utf-8") for path in alerts.iterdir())
    assert "denied" not in text
    _assert_secret_hidden(text)
    _assert_secret_hidden(str(raised.value))


@pytest.mark.parametrize("raw", ["{", "[]", "12"])
def test_relogin_malformed_secrets_file(tmp_path, raw, monkeypatch):
    alerts, locks = _dirs(tmp_path)
    secrets = tmp_path / "box-secrets.json"
    secrets.write_text(raw, encoding="utf-8")
    monkeypatch.setenv("SECTURA_WEB_PASSWORD", SECRET)
    launched = []
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="login_url",
            launcher=lambda **kwargs: launched.append(kwargs),
            alerts=alerts,
            locks=locks,
            env={},
            secrets_file=secrets,
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "secrets_file_malformed"
    assert launched == []
    text = "".join(path.read_text(encoding="utf-8") for path in alerts.iterdir())
    assert text == (
        "Chief of Staff: Sectura website sign-in stopped fail-closed.\n"
        "trigger: login_url\n"
        "page_state: secrets_file_malformed\n"
        "No further automatic sign-in this run.\n"
    )
    _assert_secret_hidden(text)
    _assert_secret_hidden(str(raised.value))


def test_relogin_verification_page_stops(tmp_path):
    alerts, locks = _dirs(tmp_path)
    cdp = FakeCdp("verification")
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="login_redirect",
            cdp=cdp,
            launcher=lambda **kwargs: (_ for _ in ()).throw(AssertionError("launched")),
            alerts=alerts,
            locks=locks,
            env=_env(),
            sleep=lambda _s: None,
            max_polls=2,
            port=9224,
        )
    assert raised.value.page_state == "verification_page"
    assert cdp.filled is True
    text = "".join(path.read_text(encoding="utf-8") for path in alerts.iterdir())
    assert "verification_page" in text
    assert "/Account/VerifyCode" in text
    _assert_secret_hidden(text)


def test_relogin_cooldown_refuses_second_attempt(tmp_path):
    alerts, locks = _dirs(tmp_path)
    locks.mkdir()
    (locks / "relogin-earlier.txt").write_text(
        f"epoch={time.time()}\ntrigger=login_url\npage_state=login_error\n",
        encoding="utf-8",
    )
    launched = []
    with pytest.raises(SecturaReloginError) as raised:
        attempt_sectura_relogin(
            trigger="login_url",
            launcher=lambda **kwargs: launched.append(kwargs),
            alerts=alerts,
            locks=locks,
            env=_env(),
            cooldown_s=12 * 60 * 60,
            now=time.time(),
            sleep=lambda _s: None,
            port=9224,
        )
    assert raised.value.page_state == "relogin_cooldown"
    assert launched == []
    text = "".join(path.read_text(encoding="utf-8") for path in alerts.iterdir())
    _assert_secret_hidden(text)
    _assert_secret_hidden(str(raised.value))


def test_relogin_relaunches_chrome_when_cdp_is_down(tmp_path):
    alerts, locks = _dirs(tmp_path)
    cdp = FakeCdp("relaunch")
    launched: list[int] = []

    def _launch(*, port: int) -> None:
        launched.append(port)
        cdp.up = True

    attempt_sectura_relogin(
        trigger="no_sectura_tab",
        cdp=cdp,
        launcher=_launch,
        alerts=alerts,
        locks=locks,
        env=_env(),
        sleep=lambda _s: None,
        max_polls=3,
        port=9224,
    )
    assert launched == [9224]
    assert cdp.filled is True
    command = chrome_incognito_command(9224)
    assert "--incognito" in command
    assert "--remote-debugging-port=9224" in command
    assert LOGIN_URL in command
    assert chrome_launch_env()["DISPLAY"] == ":2"
