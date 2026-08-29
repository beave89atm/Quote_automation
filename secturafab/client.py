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
    cadimport_next_form,
    is_cloudflare_challenge,
    is_website_login_redirect,
    jquery_ajax_form,
    request_verification_token,
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
        token = request_verification_token(getattr(response, "text", "") or "")
        if token:
            self._request_verification_token = token
        return self._parse_website_or_raise(response)

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

    def cadimport_update_data(self, payload: Any = None) -> Any:
        """POST /CadImport/UpdateData"""
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_update_data"],
            json=None,
            data=cadimport_next_form(
                payload if isinstance(payload, dict) else {"List": payload},
                token=getattr(self, "_request_verification_token", None),
            )
            if payload is not None
            else cadimport_next_form(
                {}, token=getattr(self, "_request_verification_token", None)
            ),
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            require_session=False,
        )
        return self._parse_website_or_raise(response, require_session=False)

    def cadimport_update_data_next(self, payload: Any = None) -> Any:
        """POST /CadImport/UpdateDataNext — green Next on www CAD Files.

        List is a JSON array of objects (double quotes), never Python str(list).
        """
        if isinstance(payload, dict):
            body = build_cadimport_next_payload(
                str(payload.get("ID") or payload.get("quoteID") or ""),
                payload.get("List"),
                list_other=payload.get("ListOther"),
            )
        else:
            body = build_cadimport_next_payload("", payload)
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_update_data_next"],
            json=None,
            data=cadimport_next_form(
                body, token=getattr(self, "_request_verification_token", None)
            ),
            headers=self._cadimport_ajax_headers(),
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
        """POST /CadImport/SetPartMode — PartMode is an integer (strings 500)."""
        params: dict[str, Any] = {"ID": row_id, "PartMode": int(part_mode)}
        if extra:
            params.update(extra)
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

    def cadimport_convert_to(self, payload: Any = None) -> Any:
        """POST /CadImport/ConvertTo"""
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["cadimport_convert_to"],
            json=payload,
            headers=self._cadimport_ajax_headers(),
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
        """POST /Quote/AddItem_DXFFiles — green Finish (JS contract)."""
        payload = build_dxf_finish_payload(
            quote_id,
            file_list,
            item_id=item_id,
            customer_material=customer_material,
        )
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["add_item_dxf_files"],
            json=payload,
            headers=self._cadimport_ajax_headers(),
            prefer_api_origin=False,
            www_only=True,
            timeout=max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_website_or_raise(response)

    def add_item_pdf_files(
        self,
        *,
        quote_id: str,
        file_list: list[dict[str, Any]],
        item_id: str | None = None,
        customer_material: bool = False,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
    ) -> Any:
        """POST /Quote/AddItem_PDFFiles — Image Files Finish (OnAddPDFClick)."""
        from .browser_session import effective_website_cookie

        if not effective_website_cookie(self.config):
            raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)
        payload = build_pdf_finish_payload(
            quote_id,
            file_list,
            item_id=item_id,
            customer_material=customer_material,
        )
        del files  # OnAddPDFClick is urlencoded {ID, ItemID, FileList}, not multipart
        response = self.website_request(
            "POST",
            WEBSITE_FINISH_PATHS["add_item_pdf_files"],
            json=None,
            data=jquery_ajax_form(payload),
            files=None,
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
