from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from typing import Any, Iterable
from urllib import error, request

from .wrappers.function_search import FunctionSearchMixin
from .wrappers.function_warapper import FunctionWrapper
from .wrappers.helpers import HellperWrapper


DEFAULT_BASE_URLS = [
    "https://webstation-datagate1.equityrt.com",
    "https://webstation-datagate2.equityrt.com",
    "https://webstation-datagate3.equityrt.com",
]


logger = logging.getLogger(__name__)


class EquityRTApiError(RuntimeError):
    pass


@dataclass
class AttemptError:
    base_url: str
    message: str


class EquityRTClient(FunctionSearchMixin, FunctionWrapper, HellperWrapper):
    def __init__(
        self,
        token: str | None = None,
        base_urls: Iterable[str] = DEFAULT_BASE_URLS,
        timeout: float = 15.0,
        user_agent: str = "equityrt-api-client/0.1",
    ) -> None:
        self.token = token
        self.base_urls = [url.rstrip("/") for url in base_urls]
        if not self.base_urls:
            raise ValueError("base_urls cannot be empty")
        self._last_used_base_url_index = -1
        self.timeout = timeout
        self.user_agent = user_agent

    def echo(self, version: str, echo: int, ua_cpu: str | None = "AMD64") -> Any:
        payload = {"Version": version, "Echo": echo}
        headers = {"UA-CPU": ua_cpu} if ua_cpu else None
        return self._post_jcontent(
            "/excel/dataservice/Connector.svc/json/Echo", payload, extra_headers=headers
        )
    
    add_in_info = None

    def cached_add_in(self, version: str = "2.6.5.471", token: str | None = None) -> Any:
        if self.add_in_info is None:
            self.add_in_info = self.add_in(version, token)
        return self.add_in_info

    def add_in(self, version: str = "2.6.5.471", token: str | None = None) -> Any:
        '''Information about available functions and their parameters for given version'''
        payload = {"Version": version, "Token": token or self._require_token()}
        return self._post_jcontent("/excel/dataservice/Connector.svc/json/AddIn", payload)

    def function_list_search_field(
        self,
        text: str,
        source_code: str,
        token: str | None = None,
    ) -> Any:
        ''''Search for functions and parameters matching the text.'''
        payload = {
            "Text": text,
            "SourceCode": source_code,
            "Token": token or self._require_token(),
        }
        return self._post_jcontent(
            "/excel/dataservice/Webstation.svc/json/FunctionListSearchField",
            payload,
            extra_headers={"X-Requested-With": "HttpWebRequest"},
        )

    def select_countries(
        self,
        classifications: list[Any] | None = None,
        zones: list[Any] | None = None,
        token: str | None = None,
    ) -> Any:
        '''List of countries with available data, optionally filtered by classifications and zones.'''
        payload = {
            "Token": token or self._require_token(),
            "Classifications": classifications if classifications is not None else [],
            "Zones": zones if zones is not None else [],
        }
        return self._post_jcontent(
            "/excel/dataservice/Webstation.svc/json/SelectCountries",
            payload,
            extra_headers={"X-Requested-With": "HttpWebRequest"},
        )

    def source_list(
        self,
        countries: list[str],
        token: str | None = None,
    ) -> Any:
        '''List of available sources (exchanges) for given countries.'''
        payload = {
            "Countries": countries,
            "Token": token or self._require_token(),
        }
        return self._post_jcontent(
            "/excel/dataservice/Webstation.svc/json/SourceList",
            payload,
            extra_headers={"X-Requested-With": "HttpWebRequest"},
        )

    def select_securities(
        self,
        source_code: str,
        date1: str,
        date2: str,
        classifications: dict[str, Any] | None = None,
        peers: list[Any] | None = None,
        is_financial_wizard: bool = False,
        token: str | None = None,
    ) -> Any:
        '''List of securities for given source (exchange) and date range, optionally filtered by classifications and peers.'''
        payload = {
            "Code": source_code,
            "Classifications": (
                classifications
                if classifications is not None
                else {
                    "CapsArray": [
                        "MEGACAP",
                        "BIGCAP",
                        "MIDCAP",
                        "SMALLCAP",
                        "MICROCAP",
                    ],
                    "Public": True,
                    "Private": False,
                }
            ),
            "Peers": peers if peers is not None else [],
            "Date1": date1,
            "Date2": date2,
            "IsFinancialWizard": is_financial_wizard,
            "Token": token or self._require_token(),
        }
        return self._post_jcontent(
            "/excel/dataservice/Webstation.svc/json/SelectSecurities",
            payload,
            extra_headers={"X-Requested-With": "HttpWebRequest"},
        )

    def populate_formula_grid(
        self,
        formula_object_id: str,
        source_code: str,
        grid_type: str,
        token: str | None = None,
    ) -> Any:
        '''Get sample excel formula'''
        payload = {
            "FormulaObjectId": formula_object_id,
            "SourceCode": source_code,
            "Type": grid_type,
            "Token": token or self._require_token(),
        }
        return self._post_jcontent(
            "/excel/dataservice/Webstation.svc/json/PopulateFormulaGrid",
            payload,
            extra_headers={"X-Requested-With": "HttpWebRequest"},
        )

    def authenticate(
        self,
        username: str,
        password: str,
        authentication_type: str = "UsernamePassword",
        set_as_default_token: bool = True,
    ) -> str:
        '''Authenticate with username and password to get a token for further requests.'''
        payload = {
            "Username": username,
            "Password": password,
            "AuthenticationType": authentication_type,
        }
        response = self._post_jcontent(
            "/excel/dataservice/Authentication.svc/json/Authenticate", payload
        )

        if not isinstance(response, dict):
            raise EquityRTApiError("Unexpected authenticate response format")

        status = response.get("Status")
        token = response.get("Token")
        if status != "Ok" or not isinstance(token, str) or not token:
            message = response.get("Message")
            raise EquityRTApiError(f"Authentication failed. Status={status}, Message={message}")

        if set_as_default_token:
            self.token = token

        return token

    def invoke(
        self,
        functions: list[dict[str, Any]],
        token: str | None = None,
        culture_info: dict[str, Any] | None = None,
    ) -> Any:
        '''Invoke functions with given parameters and culture info.'''
        payload: dict[str, Any] = {
            "Token": token or self._require_token(),
            "Functions": functions,
        }
        if culture_info is not None:
            payload["CultureInfo"] = culture_info
        return self._post_jcontent("/excel/dataservice/Connector.svc/json/Invoke", payload)

    def _require_token(self) -> str:
        if not self.token:
            raise ValueError("Token is required. Pass token in constructor or method call.")
        return self.token

    def _post_jcontent(
        self,
        path: str,
        inner_payload: dict[str, Any],
        extra_headers: dict[str, str | None] | None = None,
    ) -> Any:
        outer_payload = {"jcontent": json.dumps(inner_payload, separators=(",", ":"))}
        return self._post(path, outer_payload, extra_headers=extra_headers)

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        extra_headers: dict[str, str | None] | None = None,
    ) -> Any:
        attempt_errors: list[AttemptError] = []

        headers = {
            "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.1",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }
        if extra_headers:
            headers.update({k: v for k, v in extra_headers.items() if v is not None})

        body = json.dumps(payload).encode("utf-8")

        start_index = (self._last_used_base_url_index + 1) % len(self.base_urls)

        for offset in range(len(self.base_urls)):
            index = (start_index + offset) % len(self.base_urls)
            base_url = self.base_urls[index]
            url = f"{base_url}{path}"
            req = request.Request(url=url, data=body, headers=headers, method="POST")

            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    content_type = response.headers.get("Content-Type", "")
                    data = response.read()
                    self._last_used_base_url_index = index
                    return self._parse_response(data, content_type)
            except error.HTTPError as exc:
                detail = self._decode_response_body(exc.read())
                attempt_errors.append(
                    AttemptError(base_url, f"HTTP {exc.code} {exc.reason}: {detail}")
                )
            except error.URLError as exc:
                if isinstance(exc.reason, socket.timeout):
                    attempt_errors.append(AttemptError(base_url, "Timeout"))
                else:
                    attempt_errors.append(AttemptError(base_url, f"Connection error: {exc.reason}"))
            except TimeoutError:
                attempt_errors.append(AttemptError(base_url, "Timeout"))

            logger.warning("Request to %s failed: %s", base_url, attempt_errors[-1].message)

        reasons = " | ".join(f"{e.base_url}: {e.message}" for e in attempt_errors)
        raise EquityRTApiError(f"All datagates failed for {path}. {reasons}")

    @staticmethod
    def _decode_response_body(data: bytes) -> str:
        if not data:
            return ""
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return "<binary response body>"

    @staticmethod
    def _parse_response(data: bytes, content_type: str) -> Any:
        text = EquityRTClient._decode_response_body(data)
        if "application/json" in content_type or "application/octet-stream" in content_type:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                if text:
                    return text
                return data
        return text if text else data
