"""HTTP transport for provider requests (ADR-025).

Fail closed: nothing leaves the process unless the registry allows the provider. The
credential is read from the environment at send time, never stored on the request, and any
URL that reaches a message is redacted first.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.providers.canonical import NormalizationError, UnavailableReason
from app.providers.registry import ActivationDecision, ProviderRegistryEntry, activation_decision
from app.providers.resilience import parse_retry_after
from app.providers.vendors import ProviderRequest, reason_for_status

SECRET_PARAMS = frozenset({"apikey", "apiKey", "app_id", "key", "token", "access_token"})


def redact_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = [
        (name, "REDACTED" if name in SECRET_PARAMS else value)
        for name, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    payload: Any
    retry_after_seconds: float | None = None


class ProviderHttpTransport:
    def __init__(
        self,
        entry: ProviderRegistryEntry,
        environ: Mapping[str, str],
        *,
        timeout_seconds: float = 10.0,
        opener: Callable[..., Any] = urllib.request.urlopen,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        authorize: Callable[
            [ProviderRegistryEntry, Mapping[str, str]], ActivationDecision
        ] = activation_decision,
    ) -> None:
        self.entry = entry
        self._environ = environ
        self.timeout_seconds = timeout_seconds
        self._opener = opener
        self._now = now
        self._authorize = authorize

    def send(self, request: ProviderRequest) -> TransportResponse:
        decision = self._authorize(self.entry, self._environ)
        if not decision.allowed:
            reason = decision.reason or UnavailableReason.LICENSE_BLOCKED
            raise NormalizationError(
                reason, f"{self.entry.provider_id} não está ativo ({reason.value})"
            )
        if request.provider_id != self.entry.provider_id:
            raise ValueError("request belongs to another provider")
        credential = self._environ[self.entry.credential_envs[0]].strip()
        params = dict(request.params)
        headers = {"Accept": "application/json"}
        if request.auth_query_param:
            params[request.auth_query_param] = credential
        if request.auth_header:
            prefix = f"{request.auth_scheme} " if request.auth_scheme else ""
            headers[request.auth_header] = f"{prefix}{credential}"
        url = request.url + (f"?{urllib.parse.urlencode(params)}" if params else "")
        http_request = urllib.request.Request(url, headers=headers, method=request.method)
        try:
            with self._opener(http_request, timeout=self.timeout_seconds) as response:
                status, body, retry_after = response.status, response.read(), None
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
            retry_after = parse_retry_after(error.headers.get("Retry-After"), self._now())
        except TimeoutError as exc:
            raise NormalizationError(
                UnavailableReason.SOURCE_ERROR,
                f"{self.entry.provider_id} excedeu {self.timeout_seconds}s",
                retryable=True,
            ) from exc
        except urllib.error.URLError as exc:
            raise NormalizationError(
                UnavailableReason.SOURCE_ERROR,
                f"{self.entry.provider_id} inacessível em {redact_url(url)}",
                retryable=True,
            ) from exc
        try:
            payload = json.loads(body or b"null", parse_float=Decimal)
        except ValueError:
            payload = None
        if status >= 400:
            reason = reason_for_status(self.entry.provider_id, status)
            raise NormalizationError(
                reason,
                f"{self.entry.provider_id} respondeu HTTP {status}"
                + (f"; aguardar {retry_after:.0f}s" if retry_after is not None else ""),
                retryable=reason is UnavailableReason.RATE_LIMITED or status >= 500,
            )
        return TransportResponse(status, payload, retry_after)
