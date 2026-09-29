"""One Incognito sign-in when the Sectura website session is dead.

Exactly one attempt per process, and a second attempt inside the cooldown
is refused. Credentials stay in the CDP expression. They are never logged,
printed, or written to the alert or lock files. Cookies are not read.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, NoReturn
from urllib.parse import urlparse

from .chrome_cdp import SessionDeadError

LOGIN_URL = "https://www.secturafab.com/Account/Login?ReturnUrl=%2FQuote"
DEFAULT_CDP_PORT = 9224
DEFAULT_COOLDOWN_S = 12 * 60 * 60
DEFAULT_ALERT_DIR = Path("/workspace/quote-load-qc/alerts")
DEFAULT_LOCK_DIR = Path("/workspace/quote-load-qc/locks")
DEFAULT_SECRETS_PATH = Path("/home/box/agent-data/box-secrets.json")

_FILL_JS = """(function(creds) {
  var banner = "";
  try { banner = String(document.body && document.body.innerText || ""); } catch (e) {}
  if (banner.indexOf("Another user has logged in") >= 0) {
    return {ok: false, state: "license_in_use"};
  }
  var email = document.querySelector('#Email, input[name="Email"], input[type="email"]');
  var password = document.querySelector('#Password, input[name="Password"], input[type="password"]');
  if (!email || !password) return {ok: false, state: "login_form_missing"};
  email.value = creds.email;
  password.value = creds.password;
  email.dispatchEvent(new Event("input", {bubbles: true}));
  email.dispatchEvent(new Event("change", {bubbles: true}));
  password.dispatchEvent(new Event("input", {bubbles: true}));
  password.dispatchEvent(new Event("change", {bubbles: true}));
  var boxes = document.querySelectorAll('input[type="checkbox"]');
  for (var i = 0; i < boxes.length; i++) {
    var box = boxes[i];
    var label = "";
    if (box.id) {
      var lab = document.querySelector('label[for="' + box.id + '"]');
      if (lab) label = String(lab.innerText || "");
    }
    var blob = (String(box.id || "") + " " + String(box.name || "") + " " + label).toLowerCase();
    if (blob.indexOf("remember") >= 0) {
      box.checked = true;
      box.dispatchEvent(new Event("change", {bubbles: true}));
    }
  }
  var nodes = document.querySelectorAll('button, input[type="submit"], a');
  for (var j = 0; j < nodes.length; j++) {
    var node = nodes[j];
    var text = String(node.innerText || node.value || "").replace(/\\s+/g, " ").trim().toLowerCase();
    if (text === "log in" || text === "login" || text === "sign in") {
      node.click();
      return {ok: true, state: "submitted"};
    }
  }
  return {ok: false, state: "login_button_missing"};
})("""

_PROBE_JS = """(function() {
  var url = String(location.href || "");
  var title = String(document.title || "");
  var text = "";
  try { text = String(document.body && document.body.innerText || "").slice(0, 1500); } catch (e) {}
  var blob = (url + " " + title + " " + text).toLowerCase();
  var onLogin = /\\/account\\/login/.test(blob);
  return {
    url: url.split("?")[0].split("#")[0],
    title: title,
    license: blob.indexOf("another user has logged in") >= 0,
    verification: /verification code|verify your|email code|security code|two-factor|authenticator/.test(blob),
    login_error: /invalid login|login was unsuccessful|incorrect password|could not (log|sign) in/.test(blob),
    on_login: onLogin,
    on_quote: /\\/quote(\\/|$)/.test(url.toLowerCase()) && !onLogin
  };
})()"""

_attempted_this_run = False


class SecturaReloginError(SessionDeadError):
    """Sign-in stopped. page_state names the page, never a secret."""

    def __init__(self, page_state: str, *, trigger: str = "") -> None:
        self.page_state = page_state
        self.trigger = trigger
        detail = page_state if not trigger else f"{trigger}: {page_state}"
        self.reason = detail
        Exception.__init__(
            self,
            f"Sectura sign-in stopped ({detail}). Tell Chief of Staff. "
            "No further sign-in will be tried this run.",
        )


def reset_relogin_attempt_for_tests() -> None:
    global _attempted_this_run
    _attempted_this_run = False


def cdp_port() -> int:
    raw = (os.getenv("SECTURA_WEB_CDP_PORT") or os.getenv("SECTURA_CHROME_DEBUG_PORT") or "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_CDP_PORT


def cooldown_seconds() -> float:
    raw = (os.getenv("SECTURA_RELOGIN_COOLDOWN_S") or "").strip()
    try:
        value = float(raw) if raw else DEFAULT_COOLDOWN_S
    except ValueError:
        value = DEFAULT_COOLDOWN_S
    return value if value > 0 else DEFAULT_COOLDOWN_S


def alert_dir() -> Path:
    raw = (os.getenv("SECTURA_RELOGIN_ALERT_DIR") or "").strip()
    return Path(raw) if raw else DEFAULT_ALERT_DIR


def lock_dir() -> Path:
    raw = (os.getenv("SECTURA_RELOGIN_LOCK_DIR") or "").strip()
    return Path(raw) if raw else DEFAULT_LOCK_DIR


def secrets_path() -> Path:
    raw = (os.getenv("SECTURA_WEB_SECRETS_PATH") or "").strip()
    return Path(raw) if raw else DEFAULT_SECRETS_PATH


def chrome_incognito_command(port: int) -> list[str]:
    binary = (os.getenv("SECTURA_CHROME_BIN") or "google-chrome").strip() or "google-chrome"
    profile = tempfile.mkdtemp(prefix="sectura-cdp-")
    return [
        binary,
        "--incognito",
        f"--remote-debugging-port={int(port)}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        LOGIN_URL,
    ]


def chrome_launch_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DISPLAY"] = (os.getenv("SECTURA_CHROME_DISPLAY") or ":2").strip() or ":2"
    return env


def launch_chrome_incognito(*, port: int) -> None:
    """Relaunch Incognito with remote debugging. Does not read cookies."""
    subprocess.Popen(
        chrome_incognito_command(port),
        env=chrome_launch_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _http_json(url: str, timeout: float = 0.5) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    if not body:
        return None
    return json.loads(body.decode("utf-8", errors="replace"))


class ChromeCdp:
    """Live CDP on 127.0.0.1. Pages and Runtime.evaluate only."""

    def reachable(self, port: int) -> bool:
        try:
            info = _http_json(f"http://127.0.0.1:{int(port)}/json/version")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return False
        return isinstance(info, dict) and bool(info.get("webSocketDebuggerUrl") or info.get("Browser"))

    def pages(self, port: int) -> list[dict[str, Any]]:
        try:
            payload = _http_json(f"http://127.0.0.1:{int(port)}/json/list", timeout=1.0)
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return []
        if not isinstance(payload, list):
            return []
        return [
            row
            for row in payload
            if isinstance(row, dict) and str(row.get("type") or "page") == "page"
        ]

    def navigate(self, ws_url: str, url: str) -> None:
        from .chrome_cdp import cdp_call

        cdp_call(ws_url, "Page.navigate", {"url": url}, timeout=10.0)

    def evaluate(self, ws_url: str, expression: str) -> Any:
        from .chrome_cdp import _unwrap_evaluate, cdp_call

        result = cdp_call(
            ws_url,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
            timeout=15.0,
        )
        return _unwrap_evaluate(result)


def _safe_path(url: str) -> str:
    path = urlparse(str(url or "")).path or ""
    return path[:200]


def _page_state(probe: Any) -> str:
    if not isinstance(probe, dict):
        return "probe_failed"
    if probe.get("license"):
        return "license_in_use"
    if probe.get("verification"):
        return "verification_page"
    if probe.get("login_error"):
        return "login_error"
    if probe.get("on_quote") and not probe.get("on_login"):
        return "quote"
    if probe.get("on_login"):
        return "still_on_login"
    return "still_dead"


class SecretsReadError(Exception):
    """Secrets file or credential lookup failed. The message is a page state, never a value."""

    def __init__(self, page_state: str) -> None:
        self.page_state = page_state
        Exception.__init__(self, page_state)


def _secret_text(raw: Any) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise SecretsReadError("secrets_file_malformed")
    return raw.strip()


def _card_secret(payload: dict[str, Any], key: str) -> str:
    """Read card.KEY from a nested card object or a literal dotted top-level key."""
    dotted = f"card.{key}"
    card = payload.get("card") if "card" in payload else None
    if "card" in payload and not isinstance(card, dict) and dotted not in payload:
        raise SecretsReadError("secrets_file_malformed")
    nested = ""
    if isinstance(card, dict) and key in card:
        nested = _secret_text(card.get(key))
    literal = ""
    if dotted in payload:
        literal = _secret_text(payload.get(dotted))
    return nested or literal


def _read_secrets_file(path: Path) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SecretsReadError("secrets_file_missing") from None
    except OSError:
        raise SecretsReadError("secrets_file_unreadable") from None
    except UnicodeDecodeError:
        raise SecretsReadError("secrets_file_malformed") from None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise SecretsReadError("secrets_file_malformed") from None
    if not isinstance(payload, dict):
        raise SecretsReadError("secrets_file_malformed")
    email = _card_secret(payload, "SECTURA_WEB_EMAIL")
    password = _card_secret(payload, "SECTURA_WEB_PASSWORD")
    del text, payload
    return email, password


def _credentials(
    env: dict[str, str] | None = None,
    *,
    secrets_file: Path | None = None,
) -> tuple[str, str]:
    """Env vars win. A secrets file fills only the fields that are still empty."""
    source = env if env is not None else os.environ
    email = str(source.get("SECTURA_WEB_EMAIL") or "").strip()
    password = str(source.get("SECTURA_WEB_PASSWORD") or "").strip()
    if email and password:
        return email, password
    file_email, file_password = _read_secrets_file(
        secrets_file if secrets_file is not None else secrets_path()
    )
    email = email or file_email
    password = password or file_password
    del file_email, file_password
    if not email or not password:
        raise SecretsReadError("credentials_missing")
    return email, password


def _lock_page_state(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("page_state="):
            return line.split("=", 1)[1].strip()
    return ""


def _cooldown_active(folder: Path, *, now: float, cooldown_s: float) -> bool:
    """Cooldown only after a failed attempt. Success and in-progress locks do not."""
    if not folder.is_dir():
        return False
    for path in folder.glob("relogin-*.txt"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        state = _lock_page_state(text)
        if state in {"", "started", "success"}:
            continue
        for line in text.splitlines():
            if not line.startswith("epoch="):
                continue
            try:
                stamp = float(line.split("=", 1)[1].strip())
            except ValueError:
                continue
            if now - stamp < cooldown_s:
                return True
    return False


def _mark_latest_lock(folder: Path, page_state: str) -> None:
    if not folder.is_dir():
        return
    paths = sorted(folder.glob("relogin-*.txt"))
    if not paths:
        return
    path = paths[-1]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    lines = []
    seen = False
    for line in text.splitlines():
        if line.startswith("page_state="):
            lines.append(f"page_state={page_state}")
            seen = True
        else:
            lines.append(line)
    if not seen:
        lines.append(f"page_state={page_state}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_lock(folder: Path, *, trigger: str, page_state: str, now: float) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
    path = folder / f"relogin-{stamp}.txt"
    path.write_text(
        f"epoch={now}\ntrigger={trigger}\npage_state={page_state}\n",
        encoding="utf-8",
    )


def alert_chief_of_staff(
    message: str,
    *,
    folder: Path | None = None,
    on_alert: Callable[[str], None] | None = None,
    now: float | None = None,
) -> Path:
    """Write an alert that names the page state. The message must not hold secrets."""
    dest = folder if folder is not None else alert_dir()
    dest.mkdir(parents=True, exist_ok=True)
    moment = time.time() if now is None else now
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(moment))
    path = dest / f"alert-{stamp}.txt"
    path.write_text(message, encoding="utf-8")
    if on_alert is not None:
        on_alert(message)
    return path


def _alert_message(*, trigger: str, page_state: str, url_path: str = "") -> str:
    lines = [
        "Chief of Staff: Sectura website sign-in stopped fail-closed.",
        f"trigger: {trigger}",
        f"page_state: {page_state}",
    ]
    if url_path:
        lines.append(f"url_path: {url_path}")
    lines.append("No further automatic sign-in this run.")
    return "\n".join(lines) + "\n"


def _submit_login(client: ChromeCdp, ws: str, email: str, password: str) -> Any:
    """Send the form once. The expression is not logged and not attached to errors."""
    expression = _FILL_JS + json.dumps({"email": email, "password": password}) + ")"
    try:
        return client.evaluate(ws, expression)
    except Exception:
        return {"ok": False, "state": "evaluate_failed"}
    finally:
        del expression


def _fail(
    *,
    trigger: str,
    page_state: str,
    url_path: str = "",
    on_alert: Callable[[str], None] | None = None,
    alerts: Path | None = None,
    locks: Path | None = None,
) -> NoReturn:
    if locks is not None:
        _mark_latest_lock(locks, page_state)
    message = _alert_message(trigger=trigger, page_state=page_state, url_path=url_path)
    alert_chief_of_staff(message, folder=alerts, on_alert=on_alert)
    raise SecturaReloginError(page_state, trigger=trigger)


def _pick_page(pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in pages:
        if not isinstance(row, dict) or not row.get("webSocketDebuggerUrl"):
            continue
        url = str(row.get("url") or "").lower()
        if "/account/login" in url:
            rank = 0
        elif "secturafab.com" in url:
            rank = 1
        else:
            rank = 2
        ranked.append((rank, row))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    return ranked[0][1]


def sectura_tab_open(cdp: ChromeCdp | None = None, *, port: int | None = None) -> bool:
    """True when a Sectura tab is open and is not the login page."""
    client = cdp or ChromeCdp()
    debug_port = DEFAULT_CDP_PORT if port is None else port
    if port is None:
        debug_port = cdp_port()
    if not client.reachable(debug_port):
        return False
    for row in client.pages(debug_port):
        url = str(row.get("url") or "").lower()
        if "secturafab.com" in url and "/account/login" not in url:
            return True
    return False


def attempt_sectura_relogin(
    *,
    trigger: str,
    cdp: ChromeCdp | None = None,
    launcher: Callable[..., None] | None = None,
    on_alert: Callable[[str], None] | None = None,
    alerts: Path | None = None,
    locks: Path | None = None,
    now: float | None = None,
    cooldown_s: float | None = None,
    port: int | None = None,
    env: dict[str, str] | None = None,
    secrets_file: Path | None = None,
    sleep: Callable[[float], None] | None = None,
    max_polls: int = 8,
) -> None:
    """Try one sign-in. Return on /Quote. Raise SecturaReloginError otherwise."""
    global _attempted_this_run
    moment = time.time() if now is None else now
    wait = sleep or time.sleep
    debug_port = cdp_port() if port is None else int(port)
    lock_folder = locks if locks is not None else lock_dir()
    alert_folder = alerts if alerts is not None else alert_dir()
    window = DEFAULT_COOLDOWN_S if cooldown_s is None else cooldown_s
    if _attempted_this_run:
        _fail(
            trigger=trigger,
            page_state="relogin_already_attempted",
            on_alert=on_alert,
            alerts=alert_folder,
        )
    if _cooldown_active(lock_folder, now=moment, cooldown_s=window):
        _attempted_this_run = True
        _fail(
            trigger=trigger,
            page_state="relogin_cooldown",
            on_alert=on_alert,
            alerts=alert_folder,
        )
    _attempted_this_run = True
    _write_lock(lock_folder, trigger=trigger, page_state="started", now=moment)
    try:
        email, password = _credentials(env, secrets_file=secrets_file)
    except SecretsReadError as exc:
        _fail(
            trigger=trigger,
            page_state=exc.page_state,
            on_alert=on_alert,
            alerts=alert_folder,
            locks=lock_folder,
        )
    client = cdp or ChromeCdp()
    start = launcher or launch_chrome_incognito
    if not client.reachable(debug_port):
        try:
            start(port=debug_port)
        except OSError:
            _fail(
                trigger=trigger,
                page_state="chrome_launch_failed",
                on_alert=on_alert,
                alerts=alert_folder,
                locks=lock_folder,
            )
        opened = False
        for _ in range(max_polls):
            wait(0.05)
            if client.reachable(debug_port):
                opened = True
                break
        if not opened:
            _fail(
                trigger=trigger,
                page_state="cdp_unreachable",
                on_alert=on_alert,
                alerts=alert_folder,
                locks=lock_folder,
            )
    page = _pick_page(client.pages(debug_port))
    if page is None:
        _fail(
            trigger=trigger,
            page_state="chrome_no_page",
            on_alert=on_alert,
            alerts=alert_folder,
            locks=lock_folder,
        )
    ws = str(page.get("webSocketDebuggerUrl") or "")
    here = str(page.get("url") or "")
    if "/account/login" not in here.lower():
        try:
            client.navigate(ws, LOGIN_URL)
        except OSError:
            _fail(
                trigger=trigger,
                page_state="navigate_failed",
                on_alert=on_alert,
                alerts=alert_folder,
                locks=lock_folder,
            )
        wait(0.05)
    probe = client.evaluate(ws, _PROBE_JS)
    state = _page_state(probe)
    url_path = _safe_path(probe.get("url") if isinstance(probe, dict) else "")
    if state == "quote":
        _mark_latest_lock(lock_folder, "success")
        return
    if state in {"license_in_use", "verification_page"}:
        _fail(
            trigger=trigger,
            page_state=state,
            url_path=url_path,
            on_alert=on_alert,
            alerts=alert_folder,
            locks=lock_folder,
        )
    filled = _submit_login(client, ws, email, password)
    del email, password
    fill_state = str(filled.get("state") or "") if isinstance(filled, dict) else "probe_failed"
    if fill_state == "license_in_use":
        _fail(
            trigger=trigger,
            page_state="license_in_use",
            on_alert=on_alert,
            alerts=alert_folder,
            locks=lock_folder,
        )
    if fill_state != "submitted":
        _fail(
            trigger=trigger,
            page_state=fill_state or "login_form_missing",
            on_alert=on_alert,
            alerts=alert_folder,
            locks=lock_folder,
        )
    last_path = ""
    last_state = "still_dead"
    for _ in range(max_polls):
        wait(0.05)
        probe = client.evaluate(ws, _PROBE_JS)
        last_state = _page_state(probe)
        last_path = _safe_path(probe.get("url") if isinstance(probe, dict) else "")
        if last_state == "quote":
            _mark_latest_lock(lock_folder, "success")
            return
        if last_state in {"license_in_use", "verification_page", "login_error"}:
            break
    _fail(
        trigger=trigger,
        page_state=last_state,
        url_path=last_path,
        on_alert=on_alert,
        alerts=alert_folder,
        locks=lock_folder,
    )
