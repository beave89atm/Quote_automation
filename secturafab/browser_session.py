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
_DUP_HANDLE_TIMEOUT_S = 4.0
_DUP_HANDLE_MAX_PIDS = 24
_DUP_HANDLE_MAX_HANDLES = 2000
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
        try:
            keys = _browser_keys(profile["local_state"])
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
            + "). IElevator could not unwrap Local State. Fail closed — "
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
        # Chrome Default: CREATE a VSS shadow first (Chrome stays open).
        # Skipping create is a FAIL — vss= must show HRESULT / exception name.
        if is_default and _try_vss_create_copy(src, dest):
            _set_lock_bypass("vss", pin=True)
        else:
            for attempt in range(2):
                try:
                    _snapshot_sqlite_file(
                        src,
                        dest,
                        allow_vss=False,
                        allow_lock_bypass=is_default,
                    )
                    last_exc = None
                    break
                except (OSError, sqlite3.Error) as exc:
                    last_exc = exc
                    time.sleep(0.35)
            if is_default:
                _set_lock_bypass(
                    _lock_bypass_with_vss(str(_cache.get("lock_bypass") or "")),
                    pin=True,
                )
            if last_exc is not None:
                raise last_exc
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
    """sqlite backup via share/nolock URI — works while Chrome is open."""
    src_uri = src.resolve().as_uri() + "?mode=ro&nolock=1"
    src_conn = sqlite3.connect(src_uri, uri=True, timeout=1.0)
    dest_conn = sqlite3.connect(str(dest))
    try:
        src_conn.backup(dest_conn)
        dest_conn.commit()
    finally:
        dest_conn.close()
        src_conn.close()


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
    if dest.is_file() and dest.stat().st_size > 0:
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
    file_type_disk = 1

    exe_names = _browser_exe_names_for_path(src)
    ranked = _rank_browser_pids(_windows_browser_pids(exe_names))
    pids: list[int] = []
    for pid in _rm_file_pids(src) + ranked:
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
                0,
                False,
                duplicate_same_access,
            ):
                continue
            try:
                if kernel32.GetFileType(dup) != file_type_disk:
                    continue
                path = _final_path_from_handle(dup)
                if not _paths_match(path, want):
                    continue
                _read_handle_to_file(dup, dest)
                if dest.is_file() and dest.stat().st_size > 0:
                    return
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

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    buf = ctypes.create_unicode_buffer(2048)
    for flags in (0, 2):  # VOLUME_NAME_DOS, VOLUME_NAME_NT
        n = kernel32.GetFinalPathNameByHandleW(handle, buf, 2048, flags)
        if n:
            return buf.value or ""
    return ""


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


def _paths_match(got: str, want: str) -> bool:
    a = _normalize_win_path(got)
    b = _normalize_win_path(want)
    if not a or not b:
        return False
    if a == b:
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
                timeout=45,
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
        timeout=45,
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
            timeout=45,
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

_ABE_HELPER_NAME = "kannon_quote_abe.exe"
_compiled_abe_helper: Path | None = None


def _local_state_sig(path: Path) -> str:
    try:
        st = path.stat()
    except OSError:
        return str(path)
    return f"{path}:{st.st_mtime_ns}:{st.st_size}"


def _browser_keys(local_state: Path | str) -> _BrowserKeys:
    path = Path(local_state)
    sig = _local_state_sig(path)
    cached = _abe_memo.get(sig)
    if cached is not None:
        return cached
    keys = _browser_keys_uncached(path)
    _abe_memo[sig] = keys
    if len(_abe_memo) > 8:
        oldest = next(iter(_abe_memo))
        if oldest != sig:
            _abe_memo.pop(oldest, None)
    return keys


def _browser_keys_uncached(path: Path) -> _BrowserKeys:
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
        keys.v10 = _v10_os_crypt_key(enc)
    abe = os_crypt.get("app_bound_encrypted_key")
    if isinstance(abe, str) and abe.strip():
        key, status, hr = _unwrap_app_bound_key(abe)
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
    return _accept_aes_key(_dpapi_unprotect(raw))


def _app_bound_ciphertext(b64_key: str) -> bytes | None:
    """Base64-decode Local State app_bound_encrypted_key and strip APPB."""
    try:
        raw = base64.b64decode(b64_key)
    except (ValueError, TypeError):
        return None
    if raw.startswith(b"APPB"):
        raw = raw[4:]
    return raw or None


def _unwrap_app_bound_key(b64_key: str) -> tuple[bytes | None, str, str]:
    """IElevator.DecryptData unwrap. Never treat the v10 DPAPI key as ABE."""
    raw = _app_bound_ciphertext(b64_key)
    if not raw:
        return None, "failed", ""
    prep = _prepare_elevator_com()
    hr = ""
    try:
        key, hr = _elevator_decrypt(raw)
    except Exception as exc:  # noqa: BLE001 — ctypes pointer-width bugs
        key, hr = None, type(exc).__name__
    if key:
        return key, "elevator", hr
    # Path validation: IElevator compares the caller to Chrome's install dir.
    # A short-lived helper next to chrome.exe has the same trimmed path.
    try:
        key, helper_hr = _elevator_decrypt_via_chrome_dir(raw)
    except Exception as exc:  # noqa: BLE001
        key, helper_hr = None, type(exc).__name__
    hr = helper_hr or hr
    if key:
        return key, "chrome_dir", hr
    # Legacy: some older builds DPAPI-wrapped a raw 16/32-byte key.
    try:
        legacy = _accept_aes_key(_dpapi_unprotect(raw))
    except Exception:  # noqa: BLE001
        legacy = None
    if legacy:
        return legacy, "dpapi", hr
    hr = _label_classnotreg(hr, prep)
    return None, "failed", hr


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
    """COM must launch --console (RunInteractive). Bare exe hits SCM and 0x80080005."""
    try:
        exe_s = str(exe.resolve())
    except OSError:
        exe_s = str(exe)
    quoted = f'"{exe_s}"' if " " in exe_s else exe_s
    return f"{quoted} --console"


def _register_hkcu_elevator_localserver(exe: Path) -> str:
    """Per-user LocalServer32 — no admin, does not Start-Service."""
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return "winreg"
    cmd = _localserver32_cmd(exe)
    access = winreg.KEY_WRITE | winreg.KEY_READ
    if hasattr(winreg, "KEY_WOW64_64KEY"):
        access |= winreg.KEY_WOW64_64KEY
    clsids = tuple(dict.fromkeys(clsid for clsid, _ in _CHROME_ELEVATOR))
    try:
        for clsid in clsids:
            clsid_path = rf"Software\Classes\CLSID\{clsid}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, clsid_path, 0, access) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Chrome Elevation Service")
                winreg.SetValueEx(key, "AppID", 0, winreg.REG_SZ, _ELEVATOR_APPID_HKCU)
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, clsid_path + r"\LocalServer32", 0, access
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\AppID\{_ELEVATOR_APPID_HKCU}",
                0,
                access,
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Chrome Elevation Service")
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
    """--console = RunInteractive. Bare exe talks to SCM and exits (0x80080005)."""
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
    for extra in ("--console", "--unregistered-instance"):
        try:
            subprocess.Popen(  # noqa: S603 — Chrome-signed elevation_service.exe
                [str(exe), extra],
                cwd=cwd,
                close_fds=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            _launched_elevation.add(key)
            time.sleep(0.7)
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
    """Call IElevator.DecryptData (binary BSTR, local server, proxy blanket)."""
    if not blob or os.name != "nt":
        return None, ""
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


def _elevator_decrypt_via_chrome_dir(blob: bytes) -> tuple[bytes | None, str]:
    """Same DecryptData, but the process image lives under Chrome's install dir."""
    if not blob or os.name != "nt":
        return None, ""
    helper = _compiled_abe_helper_exe()
    if helper is None:
        return None, ""
    last_hr = ""
    for app_dir in _chrome_helper_dirs():
        dest = app_dir / _ABE_HELPER_NAME
        try:
            shutil.copy2(helper, dest)
        except OSError:
            continue
        try:
            key, hr = _run_abe_helper(dest, blob)
            last_hr = hr or last_hr
            if key:
                return key, last_hr
        finally:
            try:
                dest.unlink()
            except OSError:
                pass
    return None, last_hr


def _run_abe_helper(exe: Path, blob: bytes) -> tuple[bytes | None, str]:
    env = os.environ.copy()
    exes = _elevation_service_exes()
    if exes:
        env["KANNON_ELEVATION_SERVICE"] = str(exes[0])
    try:
        run = subprocess.run(
            [str(exe)],
            input=blob,
            capture_output=True,
            timeout=45,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    # stdout is the raw AES key on success — never log it.
    if run.returncode == 0:
        return _accept_aes_key(run.stdout), "0x00000000"
    return None, _hr_label(run.returncode or 0)


def _compiled_abe_helper_exe() -> Path | None:
    global _compiled_abe_helper
    if _compiled_abe_helper is not None and _compiled_abe_helper.is_file():
        return _compiled_abe_helper
    csc = _find_csc()
    if csc is None:
        return None
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
            return None
        _compiled_abe_helper = exe_path
        return exe_path
    except (OSError, subprocess.SubprocessError):
        return None


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
            return b""


# Minimal IElevator client. stdin = APPB-stripped blob; stdout = AES key only.
# Registers HKCU LocalServer32 for Chrome 151 elevation_service (no admin).
_ABE_HELPER_CS = r"""
using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32;

class K {
  [DllImport("ole32.dll")] static extern int CoInitializeEx(IntPtr p, uint f);
  [DllImport("ole32.dll")] static extern void CoUninitialize();
  [DllImport("ole32.dll")] static extern int CoCreateInstance(ref Guid c, IntPtr u, uint ctx, ref Guid i, out IntPtr o);
  [DllImport("ole32.dll")] static extern int CoSetProxyBlanket(IntPtr p, uint a, uint z, IntPtr n, uint al, uint im, IntPtr c, uint cap);
  [DllImport("ole32.dll")] static extern int CLSIDFromString([MarshalAs(UnmanagedType.LPWStr)] string s, out Guid g);
  [DllImport("oleaut32.dll")] static extern IntPtr SysAllocStringByteLen(byte[] s, uint l);
  [DllImport("oleaut32.dll")] static extern uint SysStringByteLen(IntPtr b);
  [DllImport("oleaut32.dll")] static extern void SysFreeString(IntPtr b);

  [UnmanagedFunctionPointer(CallingConvention.StdCall)]
  delegate int DecryptDel(IntPtr self, IntPtr cipher, out IntPtr plain, out uint err);

  const string Clsid = "{708860E0-F641-4611-8895-7D867DD3675B}";
  const string AppId = "{A7C0E151-0000-4ABE-B151-C0C0A1E15100}";
  const int CLASSNOTREG = unchecked((int)0x80040154);
  static readonly string[] Iids = {
    "{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
    "{8F7B6792-784D-4047-845D-1782EFBEF205}",
    "{463ABECF-410D-407F-8AF5-0DF35A005CC8}",
    "{A949CB4E-C4F9-44C4-B213-6BF8AA9AC69C}"
  };

  static void RegisterLocalServer(string exe) {
    if (string.IsNullOrEmpty(exe) || !File.Exists(exe)) return;
    string cmd = (exe.IndexOf(' ') >= 0 ? ("\"" + exe + "\"") : exe) + " --console";
    using (var k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\CLSID\" + Clsid)) {
      k.SetValue("", "Chrome Elevation Service");
      k.SetValue("AppID", AppId);
    }
    using (var k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\CLSID\" + Clsid + @"\LocalServer32"))
      k.SetValue("", cmd);
    using (var k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\AppID\" + AppId))
      k.SetValue("", "Chrome Elevation Service");
    foreach (var iid in Iids) {
      using (var k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Interface\" + iid))
        k.SetValue("", "IElevator");
      using (var k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Interface\" + iid + @"\ProxyStubClsid32"))
        k.SetValue("", "{00020424-0000-0000-C000-000000000046}");
    }
  }

  static string FindService() {
    string env = Environment.GetEnvironmentVariable("KANNON_ELEVATION_SERVICE");
    if (!string.IsNullOrEmpty(env) && File.Exists(env)) return env;
    try {
      string here = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
      if (!string.IsNullOrEmpty(here)) {
        string next = Path.Combine(here, "elevation_service.exe");
        if (File.Exists(next)) return next;
        var parent = Directory.GetParent(here);
        if (parent != null) {
          next = Path.Combine(parent.FullName, "elevation_service.exe");
          if (File.Exists(next)) return next;
        }
      }
    } catch {}
    return "";
  }

  static void StartConsole(string exe) {
    if (string.IsNullOrEmpty(exe) || !File.Exists(exe)) return;
    try {
      var psi = new System.Diagnostics.ProcessStartInfo();
      psi.FileName = exe;
      psi.Arguments = "--console";
      psi.WorkingDirectory = Path.GetDirectoryName(exe) ?? "";
      psi.UseShellExecute = false;
      psi.CreateNoWindow = true;
      System.Diagnostics.Process.Start(psi);
      System.Threading.Thread.Sleep(700);
    } catch {}
  }

  [STAThread]
  static int Main() {
    byte[] blob;
    using (var stdin = Console.OpenStandardInput())
    using (var ms = new MemoryStream()) {
      stdin.CopyTo(ms);
      blob = ms.ToArray();
    }
    if (blob.Length < 8) return 2;
    string svc = FindService();
    RegisterLocalServer(svc);
    StartConsole(svc);
    CoInitializeEx(IntPtr.Zero, 2);
    int lastHr = CLASSNOTREG;
    try {
      Guid clsid;
      if (CLSIDFromString(Clsid, out clsid) != 0) return 3;
      foreach (var ids in Iids) {
        Guid iid;
        if (CLSIDFromString(ids, out iid) != 0) continue;
        IntPtr punk;
        int hr = CoCreateInstance(ref clsid, IntPtr.Zero, 4, ref iid, out punk);
        lastHr = hr;
        if (hr < 0 || punk == IntPtr.Zero) continue;
        CoSetProxyBlanket(punk, 0xFFFFFFFF, 0xFFFFFFFF, IntPtr.Zero, 6, 3, IntPtr.Zero, 0x40);
        IntPtr vtbl = Marshal.ReadIntPtr(punk);
        IntPtr pfn = Marshal.ReadIntPtr(vtbl, 5 * IntPtr.Size);
        DecryptDel dec = (DecryptDel)Marshal.GetDelegateForFunctionPointer(pfn, typeof(DecryptDel));
        IntPtr bstr = SysAllocStringByteLen(blob, (uint)blob.Length);
        IntPtr plain;
        uint last;
        hr = dec(punk, bstr, out plain, out last);
        SysFreeString(bstr);
        lastHr = hr;
        if (hr >= 0 && plain != IntPtr.Zero) {
          uint n = SysStringByteLen(plain);
          byte[] key = new byte[n];
          Marshal.Copy(plain, key, 0, (int)n);
          SysFreeString(plain);
          Console.OpenStandardOutput().Write(key, 0, key.Length);
          return 0;
        }
      }
      return lastHr;
    } finally {
      CoUninitialize();
    }
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
