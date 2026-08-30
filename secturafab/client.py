from __future__ import annotations

from typing import Any

import requests

from .auth import AccessToken, SecturaFabAuthError, fetch_access_token
from .config import SecturaFabConfig
from .forbidden_quotes import ForbiddenQuoteError, refuse_forbidden_quote_write
from .website import (
    EMPTY_GUID,
    WEBSITE_AUTH_GAP,
    WEBSITE_FINISH_PATHS,
    WEBSITE_SESSION_EXPIRED,
    SecturaFabWebsiteAuthError,
    build_add_feature_payload,
    build_cadimport_next_payload,
    build_copy_move_assembly_payload,
    build_dxf_finish_payload,
    build_linear_add_payload,
    build_pdf_finish_payload,
    build_weld_add_operation_payload,
    cadimport_list_is_native_array,
    client_antiforgery_extracted,
    is_cloudflare_challenge,
    is_website_login_redirect,
    jquery_ajax_form,
    request_verification_fields,
)


def _forbid_write_payload(json_body: Any, data: Any) -> Any:
    """Quote ID for the forbid check — form POSTs send ID in data, not json."""
    if isinstance(json_body, dict):
        return json_body
    if isinstance(data, dict):
        return data
    if isinstance(data, (list, tuple)):
        out: dict[str, Any] = {}
        for item in data:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            key = str(item[0])
            if key in {"ID", "QuoteID"} and item[1] not in (None, ""):
                out[key] = item[1]
        if out:
            return out
    return json_body


class SecturaFabApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class SecturaFabClient:
    """Thin authenticated HTTP client for SecturaFAB REST endpoints."""

    def __init__(
        self,
        config: SecturaFabConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config or SecturaFabConfig.from_env()
        self.session = session or requests.Session()
        self._token: AccessToken | None = None
        self._request_verification_token: str | None = None
        self._request_verification_fields: list[tuple[str, str]] = []
        self._last_item_add_view_html: str = ""
        self._af_source: str = ""
        self._chrome_user_agent: str = ""
        self._chrome_cookie_name_diff: dict[str, list[str]] = {}
        self._cookie_quote_access_denied: bool = False
        self._website_cookie_override: str = ""
        self._quotes_tab_live: bool = False
        self._part_create_via: str = ""
        self._part_create_from_edit: bool | None = None
        self._finish_via: str = ""
        self._grid_dxf_row_count: int | None = None
        self._part_create_list_len: int | None = None
        self._part_create_internaldata_empty: bool | None = None
        self._part_create_imagestring_empty: bool | None = None
        self._part_create_payload: dict[str, Any] | None = None
        self._part_create_name_tokens: dict[str, int] | None = None
        self._part_create_form_shape: dict[str, Any] | None = None
        self._part_create_img_hw: bool | None = None
        self._part_create_af_present: bool | None = None
        self._grid_present: bool | None = None
        self._edit_quote_id: str = ""
        self._minted_id: str = ""
        self._edit_gate: str = ""
        self._stale_grid: bool = False
        self._kendo_row_keys: list[str] | None = None

    def authenticate(self, force: bool = False) -> AccessToken:
        if self._token and not self._token.is_expired and not force:
            return self._token
        self._token = fetch_access_token(self.config, session=self.session)
        return self._token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        allow_absolute: bool = False,
        retry_on_auth_error: bool = True,
    ) -> requests.Response:
        try:
            refuse_forbidden_quote_write(
                method=method,
                path=path,
                payload=_forbid_write_payload(json, data),
            )
        except ForbiddenQuoteError as exc:
            raise SecturaFabApiError(str(exc)) from exc
        token = self.authenticate()
        if path.startswith("http://") or path.startswith("https://"):
            if not allow_absolute:
                raise ValueError("Absolute URLs require allow_absolute=True")
            url = path
        else:
            url = f"{self.config.api_root}/{path.lstrip('/')}"

        req_headers = {
            "Accept": "application/json",
            "Authorization": token.authorization_header,
        }
        if headers:
            req_headers.update(headers)

        response = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            data=data,
            headers=req_headers,
            timeout=self.config.timeout_seconds,
        )

        if response.status_code in (401, 403) and retry_on_auth_error:
            self.authenticate(force=True)
            assert self._token is not None
            req_headers["Authorization"] = self._token.authorization_header
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=req_headers,
                timeout=self.config.timeout_seconds,
            )

        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        """GET JSON with short retries on Cloudflare/origin overload (502/503/504)."""
        import time

        retries = int(kwargs.pop("retries", 4))
        last_exc: SecturaFabApiError | None = None
        for attempt in range(1, max(1, retries) + 1):
            response = self.request("GET", path, **kwargs)
            try:
                return self._parse_or_raise(response)
            except SecturaFabApiError as exc:
                last_exc = exc
                if exc.status_code not in {500, 502, 503, 504} or attempt >= retries:
                    raise
                time.sleep(min(12.0, 1.5 * attempt))
        assert last_exc is not None
        raise last_exc

    def post_json(self, path: str, payload: Any = None, **kwargs: Any) -> Any:
        response = self.request("POST", path, json=payload, **kwargs)
        return self._parse_or_raise(response)

    def put_json(self, path: str, payload: Any = None, **kwargs: Any) -> Any:
        response = self.request("PUT", path, json=payload, **kwargs)
        return self._parse_or_raise(response)

    def delete_json(self, path: str, **kwargs: Any) -> Any:
        response = self.request("DELETE", path, **kwargs)
        if response.status_code == 204:
            return None
        return self._parse_or_raise(response)

    def post_multipart(
        self,
        path: str,
        *,
        files: list[tuple[str, tuple[str, Any, str]]],
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """
        POST multipart/form-data (CAD / drawing uploads).

        `files` entries are requests-style:
          ("files", (filename, fileobj, content_type))
        """
        token = self.authenticate()
        url = f"{self.config.api_root}/{path.lstrip('/')}"
        req_headers = {
            "Accept": "application/json",
            "Authorization": token.authorization_header,
        }
        if headers:
            req_headers.update(headers)
        # Do not set Content-Type — requests adds the multipart boundary.
        response = self.session.post(
            url,
            params=params,
            files=files,
            headers=req_headers,
            timeout=timeout or max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_or_raise(response)

    def whoami(self) -> Any:
        """Best-effort current-user probe across common Account routes."""
        candidates = [
            "Account/UserInfo",
            "Account/Me",
            "account/userinfo",
            "Users/Me",
            "User",
        ]
        errors: list[str] = []
        for path in candidates:
            response = self.request("GET", path, retry_on_auth_error=False)
            if response.status_code < 400:
                return self._parse_or_raise(response)
            errors.append(f"{path} -> {response.status_code}")
        raise SecturaFabApiError(
            "Could not resolve current user via known Account routes: "
            + "; ".join(errors)
        )

    def _auth_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        token = self.authenticate()
        headers = {
            "Accept": "application/json, text/html",
            "Authorization": token.authorization_header,
        }
        from .browser_session import effective_website_cookie

        cookie = getattr(self, "_website_cookie_override", None)
        if not (isinstance(cookie, str) and cookie.strip()):
            cookie = effective_website_cookie(self.config)
        if cookie:
            headers["Cookie"] = cookie
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _cadimport_ajax_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
        """QuoteOrderEdit jQuery ajax header so MVC returns JSON, not a view string."""
        headers = {"X-Requested-With": "XMLHttpRequest"}
        if extra:
            headers.update(extra)
        return headers

    def _quote_page_ajax_headers(
        self, extra: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Same-origin $.ajax from /Quote: XHR + Referer + optional AF headers.

        DoCreateDXFParts does not set these; the browser does. Live 34639-1
        /part/create 403+LogOnUrl with CadImport 200 on the same cookie.
        """
        root = self.config.website_root.rstrip("/")
        headers = self._cadimport_ajax_headers(
            {
                "Referer": f"{root}/Quote",
                "Origin": root,
                "Accept": "application/json, text/javascript, */*; q=0.01",
            }
        )
        token = getattr(self, "_request_verification_token", None)
        if isinstance(token, str) and token.strip():
            # kendo.antiForgeryTokens merges into data only; some MVC AF
            # filters also read the RequestVerificationToken header.
            headers["RequestVerificationToken"] = token
            headers["__RequestVerificationToken"] = token
        ua = getattr(self, "_chrome_user_agent", None)
        if isinstance(ua, str) and ua.strip():
            headers["User-Agent"] = ua
        if extra:
            headers.update(extra)
        return headers

    def _website_origins(self, *, prefer_api_origin: bool = False) -> list[str]:
        website = self.config.website_root.rstrip("/")
        api = self.config.base_url.rstrip("/")
        origins = [website, api] if not prefer_api_origin else [api, website]
        seen: set[str] = set()
        out: list[str] = []
        for origin in origins:
            if origin and origin not in seen:
                seen.add(origin)
                out.append(origin)
        return out

    def website_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        headers: dict[str, str] | None = None,
        prefer_api_origin: bool = False,
        www_only: bool = False,
        require_session: bool = True,
        timeout: float | None = None,
        retry_on_auth_error: bool = False,
        omit_authorization: bool = False,
    ) -> requests.Response:
        """
        Hit a www MVC route (no /api prefix). Never PATCH a forbidden live quote.

        CadImport MVC (Upload / Next / Data / SetUnits / GetDXFData) is the
        signed-in www.secturafab.com Quotes UI. www_only=True for those
        actions — do not fall through a www 500/404 to api (live 1002381-1
        SetUnits/GetDXFData logged api after www already failed).
        /Quote/AddItem_DXFFiles (CAD Files Finish) still 302s without a cookie.
        Image Files (AddItem_PDFFiles) and Long (AddItem_Linear) are tried
        with bearer on every origin; a 302 is not an excuse to ship empty packs.
        """
        try:
            refuse_forbidden_quote_write(
                method=method,
                path=path,
                payload=_forbid_write_payload(json, data),
            )
        except ForbiddenQuoteError as exc:
            raise SecturaFabApiError(str(exc)) from exc
        req_headers = self._auth_headers(headers)
        if omit_authorization:
            req_headers.pop("Authorization", None)
        last: requests.Response | None = None
        last_cf = False
        if www_only:
            origins = [self.config.website_root.rstrip("/")]
        else:
            origins = self._website_origins(prefer_api_origin=prefer_api_origin)
        for origin in origins:
            url = f"{origin}/{path.lstrip('/')}"
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                files=files,
                headers=req_headers,
                timeout=timeout or self.config.timeout_seconds,
                allow_redirects=False,
            )
            last = response
            location = response.headers.get("Location") or ""
            if is_website_login_redirect(response.status_code, location):
                if require_session:
                    raise SecturaFabWebsiteAuthError(
                        f"{WEBSITE_SESSION_EXPIRED} — {WEBSITE_AUTH_GAP}",
                        status_code=response.status_code,
                        body=location,
                    )
                # Cookie-less: try the next origin with the same bearer.
                continue
            if is_cloudflare_challenge(response.status_code, response.text):
                last_cf = True
                continue
            # API host: CadImport SetUnits 500, GetDXFData 404 (live 1007756-3).
            # The www MVC host still serves those actions.
            if response.status_code in (404, 405) or response.status_code >= 500:
                continue
            if (
                response.status_code in (401, 403)
                and retry_on_auth_error
                and not is_cloudflare_challenge(response.status_code, response.text)
            ):
                self.authenticate(force=True)
                req_headers = self._auth_headers(headers)
                if omit_authorization:
                    req_headers.pop("Authorization", None)
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                    headers=req_headers,
                    timeout=timeout or self.config.timeout_seconds,
                    allow_redirects=False,
                )
                last = response
            return response
        if last is not None and last_cf:
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP
                + " Cloudflare blocked www.secturafab.com from this host.",
                status_code=last.status_code,
                body="cloudflare_challenge",
            )
        if last is None:
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        return last

    def _parse_website_or_raise(
        self,
        response: requests.Response,
        *,
        require_session: bool = True,
    ) -> Any:
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            if require_session:
                raise SecturaFabWebsiteAuthError(
                    f"{WEBSITE_SESSION_EXPIRED} — {WEBSITE_AUTH_GAP}",
                    status_code=response.status_code,
                    body=location,
                )
            return None
        if is_cloudflare_challenge(response.status_code, response.text):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP
                + " Cloudflare blocked www.secturafab.com from this host.",
                status_code=response.status_code,
                body="cloudflare_challenge",
            )
        return self._parse_or_raise(response)

    def probe_website_finish_auth(self) -> dict[str, Any]:
        """
        GET /Quote/GetItem_AddView with a dummy ID.

        Live check (2026-08-24): API bearer → 302 /Account/Login on the API
        host; www origin is Cloudflare-challenged from this environment.
        CadImport routes accept the same bearer.
        """
        from .browser_session import effective_website_cookie

        try:
            response = self.website_request(
                "GET",
                WEBSITE_FINISH_PATHS["get_item_add_view"],
                params={"ID": EMPTY_GUID, "ItemType": "dxf"},
                require_session=False,
                prefer_api_origin=True,
            )
        except SecturaFabWebsiteAuthError as exc:
            return {
                "ok": False,
                "can_finish": False,
                "status_code": exc.status_code,
                "gap": WEBSITE_AUTH_GAP,
                "website_root": self.config.website_root,
                "has_website_cookie": bool(effective_website_cookie(self.config)),
            }
        location = response.headers.get("Location") or ""
        login = is_website_login_redirect(response.status_code, location)
        html_ok = response.status_code < 400 and "login" not in (
            response.text[:400].lower()
        )
        return {
            "ok": html_ok and not login,
            "can_finish": html_ok and not login,
            "status_code": response.status_code,
            "location": location or None,
            "gap": None if (html_ok and not login) else WEBSITE_AUTH_GAP,
            "website_root": self.config.website_root,
            "has_website_cookie": bool(effective_website_cookie(self.config)),
        }

    def get_item_add_view(
        self,
        quote_id: str,
        *,
        item_type: str = "dxf",
    ) -> Any:
        """GET /Quote/GetItem_AddView?ID={quoteId}&ItemType=dxf|pdf"""
        response = self.website_request(
            "GET",
            WEBSITE_FINISH_PATHS["get_item_add_view"],
            params={"ID": quote_id, "ItemType": item_type},
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
        )
        html = getattr(response, "text", "") or ""
        self._last_item_add_view_html = html
        parsed = self._parse_website_or_raise(response)
        if isinstance(parsed, dict):
            view = parsed.get("View") or parsed.get("view") or ""
            if isinstance(view, str) and view:
                html = html + "\n" + view
                self._last_item_add_view_html = html
        self._merge_antiforgery_fields(request_verification_fields(html))
        return parsed

    def _merge_antiforgery_fields(self, fields: list[tuple[str, str]]) -> None:
        have = list(getattr(self, "_request_verification_fields", None) or [])
        seen = {str(name) for name, _ in have}
        for name, value in fields:
            if not name or not value or name in seen:
                continue
            have.append((str(name), str(value)))
            seen.add(str(name))
        self._request_verification_fields = have
        if have and not getattr(self, "_request_verification_token", None):
            self._request_verification_token = have[0][1]

    def _quote_layout_headers(self) -> dict[str, str]:
        """Full-page Quote GET: Chrome-like, no XHR, no API bearer."""
        headers = {"Accept": "text/html,application/xhtml+xml"}
        ua = getattr(self, "_chrome_user_agent", None)
        if isinstance(ua, str) and ua.strip():
            headers["User-Agent"] = ua
        return headers

    def _apply_chrome_cookies(self, pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
        """Replace in-memory website cookie from CDP. Never log values."""
        from .browser_session import effective_website_cookie
        from .chrome_cdp import (
            compare_cookie_name_presence,
            cookie_header_from_pairs,
        )

        before = getattr(self, "_website_cookie_override", None) or effective_website_cookie(
            self.config
        )
        header = cookie_header_from_pairs(pairs)
        if header:
            self._website_cookie_override = header
        names = [n for n, _ in pairs]
        return compare_cookie_name_presence(before, names)

    def harvest_chrome_antiforgery(self) -> str:
        """Hypothesis A+B: CDP cookies / Quotes DOM. Returns af_source or ''."""
        from .chrome_cdp import (
            chrome_quotes_live,
            chrome_version_user_agent,
            scrape_quotes_af_fields,
            sectura_cookies_from_cdp,
        )

        if not chrome_quotes_live():
            return ""
        ua = chrome_version_user_agent()
        if ua:
            self._chrome_user_agent = ua
        pairs = sectura_cookies_from_cdp()
        if pairs:
            self._chrome_cookie_name_diff = self._apply_chrome_cookies(pairs)
        fields = scrape_quotes_af_fields()
        if fields:
            self._merge_antiforgery_fields(fields)
            if client_antiforgery_extracted(self):
                self._af_source = "chrome_dom"
                return self._af_source
        return ""

    def _scrape_quote_layout_html(self, quote_id: str) -> bool:
        """GET /Quote layout (cookie + Chrome UA, no bearer). AddView is skipped."""
        blobs: list[str] = []
        qid = str(quote_id or "").strip()
        pages: list[tuple[str, dict[str, str] | None]] = [
            ("/Quote", {"ID": qid} if qid else None),
            ("/Quote/Edit", {"ID": qid} if qid else None),
            ("/Quote/Edit/", {"ID": qid} if qid else None),
            ("/Quote/QuoteOrderEdit", {"ID": qid} if qid else None),
        ]
        if qid:
            pages.append(("/Quote", {"id": qid}))
        headers = self._quote_layout_headers()
        access_denied = False
        for path, params in pages:
            try:
                resp = self.website_request(
                    "GET",
                    path,
                    params=params,
                    headers=headers,
                    prefer_api_origin=False,
                    www_only=True,
                    require_session=False,
                    omit_authorization=True,
                )
            except (SecturaFabApiError, SecturaFabWebsiteAuthError):
                continue
            loc = ""
            if hasattr(resp, "headers"):
                loc = resp.headers.get("Location") or ""
            status = int(getattr(resp, "status_code", 0) or 0)
            if "AccessDenied" in loc:
                access_denied = True
                continue
            if is_website_login_redirect(status, loc):
                continue
            if status in {301, 302, 303, 307, 308} and loc:
                hop = loc
                if "://" in hop:
                    from urllib.parse import urlparse

                    parsed = urlparse(hop)
                    hop = parsed.path or path
                try:
                    resp = self.website_request(
                        "GET",
                        hop,
                        params=params,
                        headers=headers,
                        prefer_api_origin=False,
                        www_only=True,
                        require_session=False,
                        omit_authorization=True,
                    )
                except (SecturaFabApiError, SecturaFabWebsiteAuthError):
                    continue
                loc = ""
                if hasattr(resp, "headers"):
                    loc = resp.headers.get("Location") or ""
                status = int(getattr(resp, "status_code", 0) or 0)
                if "AccessDenied" in loc or is_website_login_redirect(status, loc):
                    access_denied = access_denied or "AccessDenied" in loc
                    continue
            text = getattr(resp, "text", "") or ""
            if not text or status >= 400:
                continue
            if is_cloudflare_challenge(status, text):
                continue
            blobs.append(text)
        self._cookie_quote_access_denied = access_denied
        for blob in blobs:
            self._merge_antiforgery_fields(request_verification_fields(blob))
        if client_antiforgery_extracted(self):
            self._af_source = "cookie_quote_html"
            return True
        return False

    def ensure_quote_antiforgery(self, quote_id: str) -> bool:
        """AF from the live Quotes tab DOM — never cookie HTML, never AddView.

        Live 7b723b9: cookie GET /Quote 200 AF is a different claims-based
        user than the Quotes tab. That field 403s /part/create. Prefer
        chrome_dom when a Quotes tab is live. Never log values.
        """
        del quote_id
        from .chrome_cdp import chrome_quotes_live

        self._quotes_tab_live = bool(chrome_quotes_live())
        if getattr(self, "_af_source", "") == "cookie_quote_html":
            self._request_verification_fields = []
            self._request_verification_token = None
            self._af_source = ""
        source = self.harvest_chrome_antiforgery()
        if source == "chrome_dom" and client_antiforgery_extracted(self):
            self._af_source = "chrome_dom"
            return True
        # Harvest miss: leftover cookie HTML is the wrong claims user.
        self._request_verification_fields = []
        self._request_verification_token = None
        self._af_source = ""
        return False

    def harvest_cadimport_js(
        self,
        quote_id: str,
        *,
        extra_html: str | None = None,
    ) -> list[Any]:
        """Load QuoteOrderEdit / CadImport JS from the signed-in www dialog."""
        from .cadimport_js import (
            CadImportXhr,
            extract_cadimport_xhrs,
            same_origin_script,
            script_srcs,
        )

        blobs: list[str] = []
        html = extra_html or getattr(self, "_last_item_add_view_html", "") or ""
        if not html:
            try:
                self.get_item_add_view(quote_id, item_type="dxf")
                html = getattr(self, "_last_item_add_view_html", "") or ""
            except (SecturaFabApiError, SecturaFabWebsiteAuthError):
                html = ""
        if html:
            blobs.append(html)
        pages = (
            ("/Quote/QuoteOrderEdit", {"ID": quote_id}),
            ("/Quote", {"ID": quote_id}),
        )
        bundle_paths = ("/bundles/QuoteOrderEdit", "/bundles/quoteOrderEdit")
        for path, params in pages:
            try:
                resp = self.website_request(
                    "GET",
                    path,
                    params=params,
                    headers=self._cadimport_ajax_headers(),
                    prefer_api_origin=False,
                    www_only=True,
                    require_session=False,
                )
            except (SecturaFabApiError, SecturaFabWebsiteAuthError):
                continue
            text = getattr(resp, "text", "") or ""
            if text and not is_cloudflare_challenge(
                getattr(resp, "status_code", 0), text
            ):
                blobs.append(text)
                html = html + "\n" + text
        from urllib.parse import urlparse

        root = self.config.website_root.rstrip("/")
        script_paths = list(bundle_paths)
        for src in script_srcs(html, base=root):
            if not same_origin_script(src, website_root=root):
                continue
            path = urlparse(src).path or ""
            if path and path not in {p[0] for p in pages}:
                script_paths.append(path)
        seen_paths: set[str] = set()
        for path in script_paths:
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)
            try:
                resp = self.website_request(
                    "GET",
                    path,
                    headers=self._cadimport_ajax_headers(),
                    prefer_api_origin=path.startswith("/bundles/"),
                    www_only=not path.startswith("/bundles/"),
                    require_session=False,
                )
            except (SecturaFabApiError, SecturaFabWebsiteAuthError):
                continue
            text = getattr(resp, "text", "") or ""
            if text and getattr(resp, "status_code", 0) < 400:
                blobs.append(text)
        xhrs: list[CadImportXhr] = []
        seen: set[tuple[str, str, str]] = set()
        for blob in blobs:
            for xhr in extract_cadimport_xhrs(blob):
                sig = (xhr.function, xhr.method, xhr.path)
                if sig in seen:
                    continue
                seen.add(sig)
                xhrs.append(xhr)
        return xhrs

    def post_cadimport_js_xhr(
        self,
        xhr: Any,
        payload: dict[str, Any],
    ) -> Any:
        """POST/GET one XHR extracted from QuoteOrderEdit / CadImport JS."""
        headers = self._cadimport_json_headers()
        content_type = str(getattr(xhr, "content_type", "") or "")
        method = str(getattr(xhr, "method", "POST") or "POST").upper()
        path = str(getattr(xhr, "path", "") or "")
        json_body = None
        data = None
        params = None
        if method == "GET":
            params = payload or None
        elif "json" in content_type.lower() or not content_type:
            json_body = payload
        else:
            data = payload
            headers["Content-Type"] = content_type
        response = self.website_request(
            method,
            path,
            params=params,
            json=json_body,
            data=data,
            headers=headers,
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_website_or_raise(response, require_session=False)

    def upload_item_dxf_files(
        self,
        files: list[tuple[str, tuple[str, Any, str]]],
        *,
        quote_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """POST /CadImport/UploadItem_DXFFiles (Kendo saveUrl; .stp/.step allowed)."""
        query = dict(params or {})
        if quote_id:
            query.setdefault("ID", quote_id)
            query.setdefault("quoteID", quote_id)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["upload_dxf"],
            params=query or None,
            files=files,
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_website_or_raise(response, require_session=False)

    def upload_item_pdf_attachment(
        self,
        files: list[tuple[str, tuple[str, Any, str]]],
        *,
        quote_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """POST /Attachment/UploadItem_PDFFiles — Image Files plate upload."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        query = dict(params or {})
        if quote_id:
            query.setdefault("ID", quote_id)
            query.setdefault("quoteID", quote_id)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["upload_pdf_attachment"],
            params=query or None,
            files=files,
            prefer_api_origin=False,
            require_session=True,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def read_data_linear_lookup(self, product_id: str) -> Any:
        """GET /Product/Read_DataLinearlookup — 20ft/21ft productConfigID."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        response = self.website_request(
            "GET",
            WEBSITE_FINISH_PATHS["linear_lookup"],
            params={
                "ProductID": product_id,
                "productID": product_id,
                "ID": product_id,
            },
            prefer_api_origin=False,
            require_session=True,
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def cadimport_data(self, params: dict[str, Any] | None = None) -> Any:
        """GET /CadImport/Data — classify grid after upload (www MVC)."""
        response = self.website_request(
            "GET",
            WEBSITE_FINISH_PATHS["cadimport_data"],
            params=params,
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def _cadimport_json_headers(self) -> dict[str, str]:
        headers = self._cadimport_ajax_headers()
        token = getattr(self, "_request_verification_token", None)
        if token:
            headers["RequestVerificationToken"] = token
            headers["__RequestVerificationToken"] = token
        return headers

    def _cadimport_json_body(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            body = build_cadimport_next_payload(
                str(payload.get("ID") or payload.get("quoteID") or ""),
                payload.get("List"),
                list_other=payload.get("ListOther"),
                extra=payload,
            )
        else:
            body = build_cadimport_next_payload("", payload)
        if not cadimport_list_is_native_array(body) and body.get("List") != []:
            raise SecturaFabApiError(
                "CadImport List must be a native JSON array, not a string"
            )
        return body

    def cadimport_update_data(self, payload: Any = None) -> Any:
        """POST /CadImport/UpdateData — json List is a native array.

        Live 34137-1: cookie-HTTP 200 often empty str (wrong claims user).
        Quotes-tab fetch when chrome_dom is live. Do not skip classify.
        """
        from .chrome_cdp import chrome_quotes_live, post_update_data_from_quotes_tab

        body = self._cadimport_json_body(payload)
        if chrome_quotes_live() and getattr(self, "_af_source", "") == "chrome_dom":
            result = post_update_data_from_quotes_tab(body)
            if not result.get("has_antiforgery"):
                raise SecturaFabApiError(
                    "af_extracted=false — chrome_dom required, "
                    "not POSTing /CadImport/UpdateData via cookie HTTP"
                )
            status = int(result.get("status") or 0)
            if status >= 400:
                raise SecturaFabApiError(
                    f"API request failed ({status}) for chrome_dom /CadImport/UpdateData",
                    status_code=status,
                    body={k: True for k in (result.get("body_keys") or [])} or {"Error": True},
                )
            return {
                "body_keys": result.get("body_keys") or [],
                "body_type": result.get("body_type"),
                "via": "chrome_dom_fetch",
            }
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_update_data"],
            json=body,
            data=None,
            headers=self._cadimport_json_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def cadimport_update_data_next(self, payload: Any = None) -> Any:
        """POST /CadImport/UpdateDataNext — editor-only, not gold persist.

        UpdateDXF_LoadNew only after #DXFEdit is open (CADType==="DXF").
        Live leftover EDIT: WebGLCADDisp undefined. Live 34887-1 FileList 0.
        Do not call from finish_cad_files / classify→Finish. Do not invent
        WebGLCADDisp.dataGroup. Do not json.dumps the array into List.
        """
        body = self._cadimport_json_body(payload)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_update_data_next"],
            json=body,
            data=None,
            headers=self._cadimport_json_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def cadimport_set_part_mode(
        self,
        *,
        row_id: str,
        part_mode: int,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """POST /CadImport/SetPartMode — PartMode is an integer (strings 500).

        QuoteOrderEdit: data:{ID, PartMode}. Live 34137-1 cookie-HTTP 200
        empty str — Quotes-tab fetch when chrome_dom is live.
        """
        from .chrome_cdp import chrome_quotes_live, post_set_part_mode_from_quotes_tab

        params: dict[str, Any] = {"ID": row_id, "PartMode": int(part_mode)}
        if extra:
            params.update(extra)
        if chrome_quotes_live() and getattr(self, "_af_source", "") == "chrome_dom":
            result = post_set_part_mode_from_quotes_tab(
                row_id=str(row_id), part_mode=int(part_mode)
            )
            if not result.get("has_antiforgery"):
                raise SecturaFabApiError(
                    "af_extracted=false — chrome_dom required, "
                    "not POSTing /CadImport/SetPartMode via cookie HTTP"
                )
            status = int(result.get("status") or 0)
            if status >= 400:
                raise SecturaFabApiError(
                    f"API request failed ({status}) for chrome_dom /CadImport/SetPartMode",
                    status_code=status,
                    body={k: True for k in (result.get("body_keys") or [])} or {"Error": True},
                )
            return {
                "body_keys": result.get("body_keys") or [],
                "body_type": result.get("body_type"),
                "via": "chrome_dom_fetch",
            }
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_set_part_mode"],
            params=params,
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def cadimport_set_units(self, units: str = "inch") -> Any:
        """POST /CadImport/SetUnits?units= — one key, www only.

        units+Units (query and json) 500s ASP.NET 'same key has already been
        added' (live 1002381-1). Do not hit the API host.
        """
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_set_units"],
            params={"units": units},
            json=None,
            data=None,
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def create_dxf_parts(
        self,
        id_list: list[str],
        unit_list: list[str],
        *,
        location: str = "",
        other_file_ids: list[str] | None = None,
        height: int | float = 0,
        width: int | float = 0,
        quote_id: str | None = None,
        quote_number: str | None = None,
        replace_grid: bool = True,
    ) -> Any:
        """Explode via page $.ajax /part/create (Upload IDs), then bind t.List.

        Live Skin Assembly 5b622a0d: page $.ajax on EDIT + #img H/W still
        returned InternalData empty 8/8. Fetch-vs-$.ajax is not the miss.
        Server never fills InternalData on explode. Do not invent
        InternalData. Do not eval createAllParts as explode (34632-2 List=0).

        Live 34137-2: CDP fetch with Upload file IDs → t.List>1. fetch does
        not run DoCreateDXFParts success, so #gridDXFParts stays empty.
        Live 34632-2: page createAllParts on the Quotes list posts empty
        #gridDXF IDList → t.List=0.

        Cookie-file HTTP POST 403s (live 7b723b9). Fail closed if chrome_dom
        is missing, List=0, or #gridDXFParts is missing/empty (34632-2).
        Bind and Finish a 1-row Cad piece-part (live 11796-1).
        """
        from .cadimport_js import (
            build_create_dxf_parts_fields,
            jquery_ajax_form,
            part_create_form_shape,
        )
        from .chrome_cdp import (
            bind_do_create_dxf_parts_success,
            cad_dialog_img_hw,
            chrome_quotes_live,
            post_part_create_from_quotes_tab,
        )

        if chrome_quotes_live():
            self.harvest_chrome_antiforgery()
        if getattr(self, "_af_source", "") != "chrome_dom":
            raise SecturaFabApiError(
                "af_extracted=false — chrome_dom required, "
                "not POSTing /part/create via cookie HTTP"
            )
        img_hw = False
        if chrome_quotes_live() and (not height or not width):
            hw = cad_dialog_img_hw()
            img_hw = bool(hw.get("from_img"))
            if img_hw:
                if not height:
                    height = hw.get("height") or 0
                if not width:
                    width = hw.get("width") or 0
        self._part_create_img_hw = img_hw
        fields = build_create_dxf_parts_fields(
            [
                {"SourceDataID": sid, "Units": units}
                for sid, units in zip(id_list, unit_list)
            ],
            location=location,
            other_file_ids=other_file_ids,
            height=height,
            width=width,
        )
        form = jquery_ajax_form(fields)
        self._part_create_form_shape = part_create_form_shape(
            form, height=height, width=width
        )
        result = post_part_create_from_quotes_tab(form, quote_id=quote_id)
        self._part_create_via = str(result.get("via") or "chrome_dom_fetch")
        self._part_create_from_edit = bool(result.get("from_edit"))
        self._part_create_af_present = bool(result.get("has_antiforgery"))
        if not result.get("has_antiforgery"):
            raise SecturaFabApiError(
                "af_extracted=false — chrome_dom required, not POSTing /part/create"
            )
        status = int(result.get("status") or 0)
        body_keys = [str(k) for k in (result.get("body_keys") or [])]
        if status >= 400:
            raise SecturaFabApiError(
                f"API request failed ({status}) for chrome_dom /part/create",
                status_code=status,
                body={key: True for key in body_keys} or {"Error": True, "LogOnUrl": True},
            )
        kids = result.get("List") if isinstance(result.get("List"), list) else []
        kids = [r for r in kids if isinstance(r, dict)]
        n_list = int(result.get("list_len") or len(kids))
        from .website import (
            part_create_list_name_tokens,
            part_create_list_payload_empty_bools,
        )

        payload = part_create_list_payload_empty_bools(kids)
        if n_list <= 0 and not replace_grid:
            # Live 1020249-1: pass-2 List=0 is not the 34632-2 first-pass miss.
            # Keep prior #gridDXFParts counts; do not bind an empty t.List.
            return {"List": kids}
        self._part_create_payload = payload
        self._part_create_name_tokens = part_create_list_name_tokens(
            kids, part_key=quote_number or ""
        )
        self._part_create_list_len = n_list
        self._part_create_internaldata_empty = payload["internaldata_empty"]
        self._part_create_imagestring_empty = payload["imagestring_empty"]
        if self._part_create_list_len <= 0:
            self._grid_dxf_row_count = 0
            return {"List": kids}
        bind = bind_do_create_dxf_parts_success(
            kids,
            quote_id=quote_id or None,
            quote_number=quote_number or None,
        )
        self._edit_quote_id = str(bind.get("edit_quote_id") or "")
        self._minted_id = str(bind.get("minted_id") or quote_id or "")
        self._edit_gate = str(bind.get("edit_gate") or "")
        self._stale_grid = bool(bind.get("stale_grid"))
        self._grid_present = bool(bind.get("grid_present"))
        self._grid_dxf_row_count = int(bind.get("grid_dxf_row_count") or 0)
        raw_keys = bind.get("kendo_row_keys")
        if isinstance(raw_keys, list):
            self._kendo_row_keys = [str(k) for k in raw_keys if str(k)]
        if not self._grid_present:
            return {"List": kids}
        return {"List": kids}

    def cadimport_convert_to(self, payload: Any = None) -> Any:
        """POST /CadImport/ConvertTo — ConvertTo(n) units, not STEP explode.

        QuoteOrderEdit: data:{IDList, Units}. Does not write #gridDXFParts.
        """
        body = self._cadimport_json_body(payload)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_convert_to"],
            json=body,
            data=None,
            headers=self._cadimport_json_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def cadimport_get_dxf_data(
        self,
        *,
        quote_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """GET GetDXFData — grid after green Next (www CadImport, then Quote)."""
        query = dict(params or {})
        if quote_id:
            query.setdefault("ID", quote_id)
            query.setdefault("quoteID", quote_id)
        last_exc: Exception | None = None
        for path_key in ("cadimport_get_dxf_data", "quote_get_dxf_data"):
            try:
                response = self.website_request(
                    "GET",
                    WEBSITE_FINISH_PATHS[path_key],
                    params=query or None,
                    headers=self._cadimport_ajax_headers(),
                    prefer_api_origin=False,
                    www_only=True,
                    require_session=False,
                )
            except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
                last_exc = exc
                continue
            if getattr(response, "status_code", 200) in {404, 405}:
                continue
            try:
                return self._parse_website_or_raise(response, require_session=False)
            except (SecturaFabApiError, SecturaFabWebsiteAuthError) as exc:
                last_exc = exc
                continue
        if last_exc:
            raise last_exc
        return {}

    def add_item_dxf_files(
        self,
        *,
        quote_id: str,
        file_list: list[dict[str, Any]],
        item_id: str | None = None,
        customer_material: bool = False,
    ) -> Any:
        """POST /Quote/AddItem_DXFFiles — page Finish (OnAddDXFClick).

        Live 34137-1: cookie-HTTP 200 empty / ItemList 0.
        Live 34137-2: Quotes-tab fetch of a Python-rebuilt FileList is the
        same empty 200 — #gridDXFParts was never bound.
        Live 34632-2: page createAllParts explode returned t.List=0.
        Invoke the 23b96a9 QuoteOrderEdit Finish fn after fetch+bind.
        Do not POST a Python-rebuilt FileList (live P001545 empty 200 /
        GET 0). Live BB2000-ASM: do not skip when EDIT matches and the
        grid is present — invoke OnAddDXFClick even if its source lacks
        the literal ``#gridDXFParts``.

        If EDIT kendo lacks CadType/Stock_X/Stock_Y after explode, that is
        a /part/create bind miss — do not Finish and do not invent geometry.
        Do not mint until a box capture shows those keys on kendo and the
        posted FileList.
        """
        from .chrome_cdp import (
            chrome_quotes_live,
            grid_dxf_count_is_stale,
            invoke_page_dxf_finish,
            minted_edit_tab_ready,
        )
        from .website import filelist_missing_cadimport_identity_keys

        del file_list
        if chrome_quotes_live():
            self.harvest_chrome_antiforgery()
        if getattr(self, "_af_source", "") != "chrome_dom":
            raise SecturaFabApiError(
                "af_extracted=false — chrome_dom required, "
                "not POSTing /Quote/AddItem_DXFFiles via cookie HTTP"
            )
        from .website import empty_griddxf_explode_miss

        n_list = getattr(self, "_part_create_list_len", None)
        present = getattr(self, "_grid_present", None)
        n_grid = getattr(self, "_grid_dxf_row_count", None)
        if empty_griddxf_explode_miss(
            grid_present=present if isinstance(present, bool) else None,
            n_grid=n_grid if isinstance(n_grid, (int, float)) else None,
            n_list=n_list if isinstance(n_list, (int, float)) else None,
        ):
            self._finish_via = "skipped"
            return self._dxf_finish_capture({}, via="skipped")
        if isinstance(present, bool) and not present:
            self._finish_via = "skipped"
            return self._dxf_finish_capture({}, via="skipped")
        if getattr(self, "_stale_grid", False) is True or grid_dxf_count_is_stale(
            n_grid if isinstance(n_grid, (int, float)) else None,
            n_list if isinstance(n_list, (int, float)) else None,
        ):
            self._finish_via = "skipped"
            self._edit_gate = "stale_grid"
            return self._dxf_finish_capture({}, via="skipped")
        kendo_keys = getattr(self, "_kendo_row_keys", None)
        if isinstance(kendo_keys, list):
            ident_miss = filelist_missing_cadimport_identity_keys(kendo_keys)
            if ident_miss:
                why = "filelist_missing_keys=" + "+".join(ident_miss)
                self._finish_via = "skipped"
                return self._dxf_finish_capture(
                    {
                        "kendo_row_keys": kendo_keys,
                        "filelist_row_keys": kendo_keys,
                        "filelist_missing_keys": ident_miss,
                        "filelist_missing_identity": ident_miss,
                        "finish_why": why,
                    },
                    via="skipped",
                )
        gate = minted_edit_tab_ready(quote_id, navigate=True)
        self._edit_quote_id = str(gate.get("edit_quote_id") or "")
        self._minted_id = str(gate.get("minted_id") or quote_id or "")
        if not gate.get("ok"):
            self._finish_via = "skipped"
            self._edit_gate = str(gate.get("reason") or "edit_quote_id!=minted_id")
            return self._dxf_finish_capture({}, via="skipped")
        page = invoke_page_dxf_finish(quote_id=quote_id)
        via = str(page.get("via") or "")
        if via == "skipped" or page.get("edit_gate"):
            self._finish_via = "skipped"
            if page.get("edit_gate"):
                self._edit_gate = str(page.get("edit_gate") or self._edit_gate)
            return self._dxf_finish_capture(page, via="skipped")
        page_grid = page.get("grid_dxf_row_count")
        if grid_dxf_count_is_stale(
            int(page_grid) if isinstance(page_grid, (int, float)) else None,
            int(n_list) if isinstance(n_list, (int, float)) else None,
        ):
            self._finish_via = "skipped"
            self._edit_gate = "stale_grid"
            return self._dxf_finish_capture({}, via="skipped")
        if via != "page_fn":
            # Live P001545: reconstructed FileList POST is empty 200 / GET 0.
            # Live BB2000-ASM: skip after EDIT+equal grid is a fail — the
            # page fn must have been invoked (via=page_fn), even without
            # ``#gridDXFParts`` in its source.
            self._finish_via = "skipped"
            return self._dxf_finish_capture(page, via="skipped")
        self._finish_via = "page_fn"
        status = int(page.get("status") or 0)
        if status >= 400:
            raise SecturaFabApiError(
                f"API request failed ({status}) for page_fn /Quote/AddItem_DXFFiles",
                status_code=status,
                body={key: True for key in (page.get("body_keys") or [])}
                or {"Error": True},
            )
        return self._dxf_finish_capture(page, via="page_fn")

    @staticmethod
    def _dxf_finish_capture(result: dict[str, Any], *, via: str) -> dict[str, Any]:
        body_keys = [str(k) for k in (result.get("body_keys") or [])]
        return {
            "status": int(result.get("status") or 0),
            "body_keys": body_keys,
            "body_type": result.get("body_type") or "empty",
            "has_NewItem": bool(result.get("has_NewItem")),
            "has_QuoteItem": bool(result.get("has_QuoteItem")),
            "text_len": int(result.get("text_len") or 0),
            "via": via,
            "finish_fn": str(result.get("finish_fn") or ""),
            "reads_kendo": bool(result.get("reads_kendo")),
            "finish_filelist_n": int(result.get("finish_filelist_n") or 0),
            "grid_dxf_row_count": int(result.get("grid_dxf_row_count") or 0),
            "request_keys": [str(k) for k in (result.get("request_keys") or [])],
            "filelist_from_kendo": bool(result.get("filelist_from_kendo")),
            "filelist_sourcedataid_n": int(result.get("filelist_sourcedataid_n") or 0),
            "filelist_id_n": int(result.get("filelist_id_n") or 0),
            "filelist_fileid_n": int(result.get("filelist_fileid_n") or 0),
            "filelist_row_keys": [
                str(k) for k in (result.get("filelist_row_keys") or [])
            ],
            "filelist_missing_keys": [
                str(k) for k in (result.get("filelist_missing_keys") or [])
            ],
            "filelist_missing_identity": [
                str(k) for k in (result.get("filelist_missing_identity") or [])
            ],
            "kendo_row_keys": [
                str(k) for k in (result.get("kendo_row_keys") or [])
            ],
            "filelist_filetype": (
                result.get("filelist_filetype")
                if isinstance(result.get("filelist_filetype"), dict)
                else {}
            ),
            "filelist_errorstatus": result.get("filelist_errorstatus"),
            "filelist_qty": result.get("filelist_qty"),
            "filelist_filetype_value": str(result.get("filelist_filetype_value") or ""),
            "filelist_filetype_type": str(result.get("filelist_filetype_type") or ""),
            "filelist_cad_path_keys": [
                str(k) for k in (result.get("filelist_cad_path_keys") or [])
            ],
            "filelist_internaldata_empty": bool(
                result.get("filelist_internaldata_empty")
            ),
            "filelist_imagestring_empty": bool(
                result.get("filelist_imagestring_empty")
            ),
            "finish_af_present": bool(result.get("finish_af_present")),
            "finish_why": str(result.get("finish_why") or ""),
            "empty_body": (
                str(result.get("body_type") or "") in {"empty", "str"}
                and not result.get("has_NewItem")
                and not result.get("has_QuoteItem")
                and not body_keys
            ),
        }

    def add_item_pdf_files(
        self,
        *,
        quote_id: str,
        file_list: list[dict[str, Any]],
        item_id: str | None = None,
        customer_material: bool = False,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
    ) -> Any:
        """POST /Quote/AddItem_PDFFiles — page OnAddPDFClick (GetPDFData).

        Live 1001898-5: reconstructed FileList + cookie-HTTP OnAddPDFClick
        HTTP-looked success without the calculator (Cad unitcost, no PR).
        FileList must be the page PDF kendo (GetPDFData / #gridPDF) rows
        with Status>0. Do not POST a Python-built FileList.
        """
        from .browser_session import effective_website_cookie
        from .chrome_cdp import (
            chrome_quotes_live,
            invoke_page_pdf_finish,
            minted_edit_tab_ready,
        )

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        del file_list
        del files
        del item_id
        del customer_material
        if chrome_quotes_live():
            self.harvest_chrome_antiforgery()
        if getattr(self, "_af_source", "") != "chrome_dom":
            self._pdf_finish_via = "skipped"
            return self._pdf_finish_capture({}, via="skipped")
        gate = minted_edit_tab_ready(quote_id, navigate=True)
        if not gate.get("ok"):
            self._pdf_finish_via = "skipped"
            return self._pdf_finish_capture(
                {"edit_gate": str(gate.get("reason") or "edit_quote_id!=minted_id")},
                via="skipped",
            )
        page = invoke_page_pdf_finish(quote_id=quote_id)
        via = str(page.get("via") or "")
        if via != "page_fn" or not page.get("filelist_from_kendo"):
            self._pdf_finish_via = "skipped"
            return self._pdf_finish_capture(page, via="skipped")
        self._pdf_finish_via = "page_fn"
        status = int(page.get("status") or 0)
        if status >= 400:
            raise SecturaFabApiError(
                f"API request failed ({status}) for page_fn /Quote/AddItem_PDFFiles",
                status_code=status,
                body={"Error": True},
            )
        return self._pdf_finish_capture(page, via="page_fn")

    @staticmethod
    def _pdf_finish_capture(result: dict[str, Any], *, via: str) -> dict[str, Any]:
        from_kendo = bool(result.get("filelist_from_kendo")) and via == "page_fn"
        return {
            "ok": from_kendo,
            "status": int(result.get("status") or 0),
            "via": via,
            "finish_fn": str(result.get("finish_fn") or ""),
            "reads_kendo": bool(result.get("reads_kendo")),
            "filelist_from_kendo": from_kendo,
            "finish_filelist_n": int(result.get("finish_filelist_n") or 0),
            "grid_pdf_row_count": int(result.get("grid_pdf_row_count") or 0),
            "grid_id": str(result.get("grid_id") or ""),
            "request_keys": [str(k) for k in (result.get("request_keys") or [])],
            "filelist_row_keys": [str(k) for k in (result.get("filelist_row_keys") or [])],
            "kendo_row_keys": [str(k) for k in (result.get("kendo_row_keys") or [])],
            "finish_af_present": bool(result.get("finish_af_present")),
            "finish_why": str(result.get("finish_why") or ""),
            "edit_gate": str(result.get("edit_gate") or ""),
        }

    def stamp_pdf_kendo_flats(
        self,
        *,
        quote_id: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Type L×W onto the page PDF kendo before OnAddPDFClick."""
        from .chrome_cdp import stamp_pdf_kendo_flats as _stamp

        return _stamp(rows, quote_id=quote_id)

    def add_item_linear(
        self,
        *,
        quote_id: str,
        product_id: str,
        qty: int = 1,
        length: float | None = None,
        material: str | None = None,
        machine: str = "Saw",
        name: str = "",
        item_id: str | None = None,
        customer_material: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """POST /Quote/AddItem_Linear — Long."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        payload = build_linear_add_payload(
            quote_id,
            product_id=product_id,
            qty=qty,
            length=length,
            material=material,
            machine=machine,
            name=name,
            item_id=item_id,
            customer_material=customer_material,
            extra=extra,
        )
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["add_item_linear"],
            json=None,
            data=jquery_ajax_form(payload),
            files=None,
            prefer_api_origin=False,
            require_session=True,
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def quote_item_read(self, quote_id: str) -> Any:
        """GET /Quote/QuoteItem_Read?ParentID=&LoadAssemblies=True."""
        response = self.website_request(
            "GET",
            WEBSITE_FINISH_PATHS["quote_item_read"],
            params={"ParentID": quote_id, "LoadAssemblies": "True"},
            prefer_api_origin=False,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def add_operation(
        self,
        *,
        quote_id: str,
        item_id: str,
        weld_inches: float,
        weld_hours: float,
        fitup_hours: float,
        setup_hours: float,
        grind_cost: float = 0.0,
    ) -> Any:
        """POST /Quote/AddOperation — weld on the assembly (Q10056 shape)."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        refuse_forbidden_quote_write(
            method="POST", path=WEBSITE_FINISH_PATHS["add_operation"], payload={"ID": quote_id}
        )
        payload = build_weld_add_operation_payload(
            quote_id,
            item_id,
            weld_inches=weld_inches,
            weld_hours=weld_hours,
            fitup_hours=fitup_hours,
            setup_hours=setup_hours,
            grind_cost=grind_cost,
        )
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["add_operation"],
            json=None,
            data=jquery_ajax_form(payload),
            files=None,
            prefer_api_origin=False,
            require_session=True,
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def copy_move_item_to_assembly(
        self,
        *,
        quote_id: str,
        item_id: str,
        assembly_id: str,
        mode: str = "Move",
    ) -> Any:
        """POST /Quote/CopyMoveItemToAssembly — kid under the top-level assembly."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        refuse_forbidden_quote_write(
            method="POST",
            path=WEBSITE_FINISH_PATHS["copy_move_to_assembly"],
            payload={"ID": quote_id},
        )
        payload = build_copy_move_assembly_payload(
            quote_id, item_id, assembly_id, mode=mode
        )
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["copy_move_to_assembly"],
            json=None,
            data=jquery_ajax_form(payload),
            files=None,
            prefer_api_origin=False,
            require_session=True,
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def add_item_feature(
        self,
        *,
        quote_id: str,
        item_id: str,
        diameter: float,
        qty: int = 1,
        feature_type: str = "Internal",
    ) -> Any:
        """POST /Quote/AddFeature — Internal hole on a Cad plate."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        refuse_forbidden_quote_write(
            method="POST",
            path=WEBSITE_FINISH_PATHS["add_feature"],
            payload={"ID": quote_id},
        )
        payload = build_add_feature_payload(
            quote_id,
            item_id,
            diameter=diameter,
            qty=qty,
            feature_type=feature_type,
        )
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["add_feature"],
            json=None,
            data=jquery_ajax_form(payload),
            files=None,
            prefer_api_origin=False,
            require_session=True,
        )
        location = response.headers.get("Location") or ""
        if is_website_login_redirect(response.status_code, location):
            raise SecturaFabWebsiteAuthError(
                WEBSITE_AUTH_GAP,
                status_code=response.status_code,
                body=location,
            )
        return self._parse_website_or_raise(response, require_session=True)

    def nest_quote_edit(self, quote_id: str, extra: dict[str, Any] | None = None) -> Any:
        """POST /Quote/NestQuote_Edit — same nest control the UI uses."""
        payload: dict[str, Any] = {"ID": quote_id}
        if extra:
            payload.update(extra)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["nest_quote_edit"],
            json=payload,
            prefer_api_origin=True,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_website_or_raise(response)

    def nest_quote_multipart_renest(
        self,
        quote_id: str,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """POST /Quote/NestQuoteMultiPart_Renest (e.g. after 480 → 240 stock)."""
        payload: dict[str, Any] = {"ID": quote_id}
        if extra:
            payload.update(extra)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["nest_quote_renest"],
            json=payload,
            prefer_api_origin=True,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_website_or_raise(response)

    def nest_quote_api(
        self,
        quote_id: str,
        nest_type: str = "multi",
        id_list: list[str] | None = None,
    ) -> Any:
        """Documented public nest: POST /api/v1/Nest/quote/{quoteID}/{nestType}."""
        path = f"v1/Nest/quote/{quote_id}/{nest_type}"
        return self.post_json(path, payload=id_list)

    @staticmethod
    def _parse_or_raise(response: requests.Response) -> Any:
        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text[:1000]
            detail = ""
            if isinstance(body, dict):
                for key in ("ExceptionMessage", "detail", "Message", "title"):
                    if body.get(key):
                        detail = f" — {body.get(key)}"
                        break
            raise SecturaFabApiError(
                f"API request failed ({response.status_code}) for {response.url}{detail}",
                status_code=response.status_code,
                body=body,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text


def ping_token_endpoint(config: SecturaFabConfig | None = None) -> dict[str, Any]:
    """
    Validate credentials by requesting a token.

    Returns a redacted summary suitable for logging.
    """
    cfg = config or SecturaFabConfig.from_env()
    try:
        token = fetch_access_token(cfg)
    except (SecturaFabAuthError, ValueError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "token_url": cfg.token_url,
            "api_base": cfg.base_url,
            "grant": "client_credentials" if cfg.uses_client_credentials else "password",
        }
    return {
        "ok": True,
        "token_type": token.token_type,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "access_token_preview": f"{token.access_token[:8]}…",
        "raw_keys": sorted((token.raw or {}).keys()),
        "token_url": cfg.token_url,
        "api_base": cfg.base_url,
        "grant": "client_credentials" if cfg.uses_client_credentials else "password",
    }
