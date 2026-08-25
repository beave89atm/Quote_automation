"""Discover Kyle's SecturaFAB website session from Chrome on this PC.

Finish (POST /Quote/AddItem_DXFFiles, AddItem_PDFFiles, AddItem_Linear) needs
the www MVC cookie. The quoting PC already has that session when Kyle is
signed into Sectura in Chrome. Read Chrome (and Edge) cookies for
www.secturafab.com / secturafab.com and assemble a Cookie header.

Do not invent a paste-cookie UX. SECTURAFAB_WEBSITE_COOKIE remains a silent
env override for service accounts — never prompt anyone to paste it.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any

SECTURA_HOST_NEEDLE = "secturafab.com"

# Auth + Cloudflare + ARR. Finish 302s without .AspNet.ApplicationCookie.
COOKIE_NAMES = (
    ".AspNet.ApplicationCookie",
    ".AspNet.Cookies",
    "ASP.NET_SessionId",
    "cf_clearance",
    "__cf_bm",
    "__cf_bm_sectura",
    "ARRAffinity",
    "ARRAffinitySameSite",
    ".AspNetCore.Cookies",
    "__RequestVerificationToken",
)

CHROME_SESSION_REQUIRED = (
    "Finish needs a live SecturaFAB Chrome session on this PC "
    "(www.secturafab.com / secturafab.com cookies). Sign into SecturaFAB in "
    "Chrome on the quoting PC, then push again. This app reads Chrome's "
    "cookies automatically — do not paste a cookie. "
    "If Chrome is already signed in and this still fails, cookies may be "
    "app-bound encrypted; keep Chrome open as the same Windows user that "
    "runs the app."
)

_CACHE_TTL_S = 30.0
_cache: dict[str, Any] = {"cookie": "", "ts": 0.0, "error": "", "source": ""}


def effective_website_cookie(cfg: Any | None = None) -> str:
    """Env/config override first, else Chrome/Edge cookies on this PC."""
    explicit = getattr(cfg, "website_cookie", None) if cfg is not None else None
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    env = (os.getenv("SECTURAFAB_WEBSITE_COOKIE") or "").strip()
    if env:
        return env
    return discover_sectura_website_cookie()


def discover_sectura_website_cookie(*, force: bool = False) -> str:
    """Return a Cookie header from Chrome/Edge, or '' if none is usable."""
    now = time.monotonic()
    if (
        not force
        and _cache["cookie"]
        and (now - float(_cache["ts"] or 0)) < _CACHE_TTL_S
    ):
        return str(_cache["cookie"])
    cookie, err, source = _discover_uncached()
    _cache["cookie"] = cookie
    _cache["ts"] = now
    _cache["error"] = err
    _cache["source"] = source
    return cookie


def last_discover_error() -> str:
    return str(_cache.get("error") or "")


def last_discover_source() -> str:
    return str(_cache.get("source") or "")


def _discover_uncached() -> tuple[str, str, str]:
    pairs_all: list[tuple[str, str]] = []
    decrypt_failures = 0
    found_hosts = 0
    source = ""
    for profile in _browser_cookie_dbs():
        rows = _read_cookie_rows(profile)
        if not rows:
            continue
        found_hosts += 1
        key = _browser_aes_key(profile["local_state"])
        for host, name, value, encrypted in rows:
            del host
            plain = (value or "").strip()
            if not plain and encrypted:
                plain = _decrypt_cookie_value(encrypted, key)
                if not plain:
                    decrypt_failures += 1
                    continue
            if name and plain:
                pairs_all.append((name, plain))
        if pairs_all:
            source = str(profile.get("label") or profile.get("cookies") or "chrome")
            break
    header = _assemble_cookie_header(pairs_all)
    if header:
        return header, "", source
    if found_hosts and decrypt_failures:
        return (
            "",
            "Found SecturaFAB cookies in Chrome but could not decrypt them "
            "(app-bound / v20 encryption). Keep Chrome signed into SecturaFAB "
            "as the same Windows user that runs this app.",
            source,
        )
    if found_hosts:
        return (
            "",
            "Chrome has a SecturaFAB host entry but no usable session cookie.",
            source,
        )
    return (
        "",
        "No Chrome/Edge cookies for www.secturafab.com on this PC.",
        "",
    )


def _browser_cookie_dbs() -> list[dict[str, Path | str]]:
    roots: list[tuple[str, Path]] = []
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        roots.append(("chrome", Path(local) / "Google" / "Chrome" / "User Data"))
        roots.append(("edge", Path(local) / "Microsoft" / "Edge" / "User Data"))
    # Linux / this cloud VM — only used if someone copied a profile here.
    home = Path.home()
    roots.append(("chrome", home / ".config" / "google-chrome"))
    roots.append(("chrome", home / ".config" / "chromium"))

    out: list[dict[str, Path | str]] = []
    seen: set[str] = set()
    for label, root in roots:
        if not root.is_dir():
            continue
        local_state = root / "Local State"
        for profile_dir in _profile_dirs(root):
            for cookies in (
                profile_dir / "Network" / "Cookies",
                profile_dir / "Cookies",
            ):
                if not cookies.is_file():
                    continue
                key = str(cookies)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    {
                        "label": f"{label}:{profile_dir.name}",
                        "cookies": cookies,
                        "local_state": local_state,
                    }
                )
    return out


def _profile_dirs(root: Path) -> list[Path]:
    names = ["Default"]
    try:
        names.extend(
            sorted(
                p.name
                for p in root.iterdir()
                if p.is_dir() and p.name.startswith("Profile")
            )
        )
    except OSError:
        pass
    return [root / n for n in names if (root / n).is_dir()]


def _read_cookie_rows(
    profile: dict[str, Path | str],
) -> list[tuple[str, str, str, bytes]]:
    src = Path(profile["cookies"])
    tmp_dir = tempfile.mkdtemp(prefix="kannon-chrome-cookies-")
    try:
        dest = Path(tmp_dir) / "Cookies"
        shutil.copy2(src, dest)
        wal = Path(str(src) + "-wal")
        shm = Path(str(src) + "-shm")
        if wal.is_file():
            shutil.copy2(wal, Path(tmp_dir) / "Cookies-wal")
        if shm.is_file():
            shutil.copy2(shm, Path(tmp_dir) / "Cookies-shm")
        conn = sqlite3.connect(str(dest))
        try:
            cur = conn.execute(
                "SELECT host_key, name, value, encrypted_value FROM cookies "
                "WHERE host_key LIKE ?",
                (f"%{SECTURA_HOST_NEEDLE}%",),
            )
            rows: list[tuple[str, str, str, bytes]] = []
            for host, name, value, encrypted in cur.fetchall():
                blob = encrypted if isinstance(encrypted, (bytes, bytearray)) else b""
                rows.append((str(host or ""), str(name or ""), str(value or ""), bytes(blob)))
            return rows
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _browser_aes_key(local_state: Path | str) -> bytes | None:
    path = Path(local_state)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    os_crypt = data.get("os_crypt") if isinstance(data, dict) else None
    if not isinstance(os_crypt, dict):
        return None
    abe = os_crypt.get("app_bound_encrypted_key")
    if isinstance(abe, str) and abe.strip():
        key = _decrypt_app_bound_key(abe)
        if key:
            return key
    enc = os_crypt.get("encrypted_key")
    if isinstance(enc, str) and enc.strip():
        try:
            raw = base64.b64decode(enc)
        except (ValueError, TypeError):
            return None
        if raw.startswith(b"DPAPI"):
            raw = raw[5:]
        return _dpapi_unprotect(raw)
    return None


def _decrypt_app_bound_key(b64_key: str) -> bytes | None:
    """Chrome v20 app-bound key. Best-effort on Windows via DPAPI / IElevator."""
    try:
        raw = base64.b64decode(b64_key)
    except (ValueError, TypeError):
        return None
    if raw.startswith(b"APPB"):
        raw = raw[4:]
    # Some builds wrap the AES key in user DPAPI after the APPB prefix.
    plain = _dpapi_unprotect(raw)
    if plain and len(plain) in {16, 32}:
        return plain
    return _elevator_decrypt(raw) or plain


def _dpapi_unprotect(blob: bytes) -> bytes | None:
    if not blob or os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_blob = DATA_BLOB(len(blob), ctypes.create_string_buffer(blob, len(blob)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            return None
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except (AttributeError, OSError, ValueError, TypeError):
        return None


def _elevator_decrypt(blob: bytes) -> bytes | None:
    """Chrome IElevator COM — only present on Windows with Chrome installed."""
    if not blob or os.name != "nt":
        return None
    try:
        import ctypes

        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        # CLSID_Elevator / IID_IElevator (Chrome). Failures are non-fatal.
        clsid = _guid("{708860E0-F641-4611-8895-7D867DD3675B}")
        iid = _guid("{A949CB4E-C4F9-44C4-B213-6BF8AA9AC69C}")
        punk = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            ctypes.byref(clsid),
            None,
            1,  # CLSCTX_INPROC_SERVER
            ctypes.byref(iid),
            ctypes.byref(punk),
        )
        if hr != 0 or not punk.value:
            return None
        # Best-effort: if COM create worked, DPAPI above already tried.
        return None
    except (AttributeError, OSError, ValueError, TypeError):
        return None


def _guid(text: str) -> Any:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    g = GUID()
    ctypes.windll.ole32.CLSIDFromString(text, ctypes.byref(g))
    return g


def _decrypt_cookie_value(blob: bytes, aes_key: bytes | None) -> str:
    if not blob:
        return ""
    prefix = blob[:3]
    if prefix in (b"v10", b"v11", b"v20") and aes_key:
        plain = _aes_gcm_decrypt(blob[3:], aes_key)
        if plain:
            return plain
    # Older Chrome: the whole blob is DPAPI.
    raw = _dpapi_unprotect(blob)
    if raw:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return ""


def _aes_gcm_decrypt(payload: bytes, key: bytes) -> str:
    if len(payload) < 16 + 16:
        return ""
    nonce = payload[:12]
    cipher_tag = payload[12:]
    ciphertext, tag = cipher_tag[:-16], cipher_tag[-16:]
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        plain = AESGCM(key).decrypt(nonce, ciphertext + tag, None)
        return plain.decode("utf-8")
    except Exception:  # noqa: BLE001 — optional crypto / bad key
        try:
            from Crypto.Cipher import AES  # type: ignore[import-untyped]

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            plain = cipher.decrypt_and_verify(ciphertext, tag)
            return plain.decode("utf-8")
        except Exception:  # noqa: BLE001
            return ""


def _assemble_cookie_header(pairs: list[tuple[str, str]]) -> str:
    """Keep last value per name; prefer known Finish cookies when present."""
    by_name: dict[str, str] = {}
    for name, value in pairs:
        if not name or not value:
            continue
        by_name[name] = value
    if not by_name:
        return ""
    # A session is usable when ASP.NET auth or at least a session id exists.
    has_auth = any(
        n in by_name
        for n in (
            ".AspNet.ApplicationCookie",
            ".AspNet.Cookies",
            ".AspNetCore.Cookies",
            "ASP.NET_SessionId",
        )
    )
    if not has_auth:
        return ""
    ordered: list[str] = []
    seen: set[str] = set()
    for name in COOKIE_NAMES:
        if name in by_name and name not in seen:
            ordered.append(f"{name}={by_name[name]}")
            seen.add(name)
    for name, value in by_name.items():
        if name in seen:
            continue
        ordered.append(f"{name}={value}")
        seen.add(name)
    return "; ".join(ordered)
