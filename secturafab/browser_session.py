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
_cache: dict[str, Any] = {
    "cookie": "",
    "ts": 0.0,
    "error": "",
    "source": "",
    "session_found": False,
    "lock_bypass": "",
}


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
    """QA-safe status. Never includes cookie values."""
    return {
        "session_found": session_found(),
        "source": last_discover_source(),
        "lock_bypass": str(_cache.get("lock_bypass") or ""),
        "error": last_discover_error(),
    }


def _discover_uncached() -> tuple[str, str, str]:
    _cache["lock_bypass"] = ""
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
            snapshot_errors.append(f"{label}: {_safe_os_error(exc)}")
            continue
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
            source = label
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
    if snapshot_errors:
        return (
            "",
            "Could not snapshot Chrome Cookies while the browser is open "
            f"({'; '.join(snapshot_errors)}). "
            "The app copies Default with a share-read handle — do not close "
            "Chrome and do not paste a cookie.",
            "",
        )
    return (
        "",
        "No Chrome/Edge cookies for www.secturafab.com on this PC.",
        "",
    )


def _safe_os_error(exc: BaseException) -> str:
    """WinError / errno only — never cookie material."""
    win = getattr(exc, "winerror", None)
    if win is not None:
        return f"WinError {win}"
    err = getattr(exc, "errno", None)
    if err is not None:
        return f"errno {err}"
    return type(exc).__name__


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
        _snapshot_sqlite_file(history, dest)
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


def _read_cookie_rows(
    profile: dict[str, Path | str | bool],
) -> list[tuple[str, str, str, bytes]]:
    src = Path(profile["cookies"])
    tmp_dir = tempfile.mkdtemp(prefix="kannon-chrome-cookies-")
    try:
        dest = Path(tmp_dir) / "Cookies"
        _snapshot_sqlite_file(src, dest)
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


def _snapshot_sqlite_file(src: Path, dest: Path) -> None:
    """Copy a Chrome SQLite DB that may be locked (WinError 32)."""
    errors: list[str] = []
    for fn in (
        _sqlite_backup_nolock,
        _win_lock_bypass_with_wal,
        _share_copy_with_wal,
        _shutil_copy_with_wal,
    ):
        try:
            if dest.exists():
                dest.unlink()
            fn(src, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                return
            errors.append(f"{getattr(fn, '__name__', type(fn).__name__)}: empty")
        except (OSError, sqlite3.Error) as exc:
            errors.append(
                f"{getattr(fn, '__name__', type(fn).__name__)}: {_safe_os_error(exc)}"
            )
            for leftover in dest.parent.glob(dest.name + "*"):
                try:
                    leftover.unlink()
                except OSError:
                    pass
    raise OSError(
        "Could not snapshot locked SQLite (" + "; ".join(errors) + ")"
    )


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


def _win_lock_bypass_with_wal(src: Path, dest: Path) -> None:
    """Bypass exclusive Chrome locks: backup privilege, handle dup, VSS."""
    if os.name != "nt":
        raise OSError("lock bypass is Windows-only")
    last: OSError | None = None
    used = ""
    for name, fn in (
        ("backup_priv", _win_backup_copy),
        ("dup_handle", _win_dup_handle_copy),
        ("vss", _win_vss_copy),
    ):
        try:
            if dest.exists():
                dest.unlink()
            fn(src, dest)
            if dest.is_file() and dest.stat().st_size > 0:
                used = name
                for suffix in ("-wal", "-shm", "-journal"):
                    side = Path(str(src) + suffix)
                    if not side.is_file():
                        continue
                    try:
                        fn(side, dest.parent / (dest.name + suffix))
                    except OSError:
                        continue
                _cache["lock_bypass"] = used
                return
        except OSError as exc:
            last = exc
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
    raise last or OSError(32, "Windows lock bypass failed")


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


def _win_createfile_copy(src: Path, dest: Path, *, flags: int = 0x80) -> None:
    import ctypes
    from ctypes import wintypes

    generic_read = 0x80000000
    share = 0x00000001 | 0x00000002 | 0x00000004
    open_existing = 3
    invalids = {-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF}

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        str(src),
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
        kernel32.CloseHandle(handle)


def _read_handle_to_file(handle: Any, dest: Path) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    file_begin = 0
    kernel32.SetFilePointer(handle, 0, None, file_begin)
    buf = ctypes.create_string_buffer(1024 * 1024)
    done = wintypes.DWORD(0)
    wrote = 0
    with dest.open("wb") as out:
        while True:
            ok = kernel32.ReadFile(handle, buf, len(buf), ctypes.byref(done), None)
            if not ok:
                raise OSError(ctypes.get_last_error() or 32, "ReadFile failed")
            if done.value == 0:
                break
            out.write(buf.raw[: done.value])
            wrote += done.value
    if wrote <= 0:
        raise OSError(32, "ReadFile returned 0 bytes")


def _win_dup_handle_copy(src: Path, dest: Path) -> None:
    """Duplicate the open Cookies handle from chrome.exe / msedge.exe (same user)."""
    import ctypes
    from ctypes import wintypes

    want = _normalize_win_path(str(src.resolve()))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    process_dup_handle = 0x0040
    process_query = 0x0400
    process_query_limited = 0x1000
    duplicate_same_access = 0x00000002
    file_type_disk = 1

    pids = _windows_browser_pids()
    if not pids:
        raise OSError(32, "No chrome.exe/msedge.exe process for handle dup")
    for pid in pids:
        hproc = kernel32.OpenProcess(process_dup_handle | process_query, False, pid)
        if not hproc:
            hproc = kernel32.OpenProcess(
                process_dup_handle | process_query_limited, False, pid
            )
        if not hproc:
            continue
        try:
            for handle_value in _process_handles(hproc):
                dup = wintypes.HANDLE()
                if not kernel32.DuplicateHandle(
                    hproc,
                    handle_value,
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
            kernel32.CloseHandle(hproc)
    raise OSError(32, "Cookies handle not found on chrome.exe/msedge.exe")


def _windows_browser_pids() -> list[int]:
    import ctypes
    from ctypes import wintypes

    names = {"chrome.exe", "msedge.exe"}
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
    buf = ctypes.create_unicode_buffer(1024)
    n = kernel32.GetFinalPathNameByHandleW(handle, buf, 1024, 0)
    if not n:
        return ""
    return buf.value or ""


def _normalize_win_path(path: str) -> str:
    text = (path or "").strip()
    if text.startswith("\\\\?\\"):
        text = text[4:]
    return text.replace("/", "\\").casefold()


def _paths_match(got: str, want: str) -> bool:
    a = _normalize_win_path(got)
    b = _normalize_win_path(want)
    return bool(a) and a == b


def _win_vss_copy(src: Path, dest: Path) -> None:
    """Read the file from a Volume Shadow Copy (works on exclusive locks)."""
    import subprocess

    src = src.resolve()
    drive = f"{src.drive}\\"
    rel = str(src)[len(src.drive) :].lstrip("\\/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "param($Drive,$Rel,$Dest)\n"
        "$ErrorActionPreference='Stop'\n"
        "$cls=[wmiclass]'\\\\.\\root\\cimv2:Win32_ShadowCopy'\n"
        "$res=$cls.Create($Drive,'ClientAccessible')\n"
        "if($res.ReturnValue -ne 0){ throw ('VSS '+$res.ReturnValue) }\n"
        "$id=$res.ShadowID\n"
        "try{\n"
        "  $sc=Get-CimInstance Win32_ShadowCopy | Where-Object {$_.ID -eq $id}\n"
        "  Copy-Item -LiteralPath ($sc.DeviceObject+'\\'+$Rel) -Destination $Dest -Force\n"
        "} finally {\n"
        "  Get-CimInstance Win32_ShadowCopy | Where-Object {$_.ID -eq $id} | "
        "Remove-CimInstance\n"
        "}\n"
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
                drive,
                rel,
                str(dest),
            ],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    if run.returncode != 0 or not dest.is_file() or dest.stat().st_size <= 0:
        # Do not include PowerShell stdout (could be noisy); code only.
        raise OSError(run.returncode or 32, "VSS snapshot copy failed")


def _win_share_copy(src: Path, dest: Path) -> None:
    """CreateFileW with FILE_SHARE_READ|WRITE|DELETE, then ReadFile."""
    _win_createfile_copy(src, dest, flags=0x80)


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
