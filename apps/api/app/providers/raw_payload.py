import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

_SENSITIVE = {"authorization", "api_key", "apikey", "token", "secret", "password"}


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: "[REDACTED]" if key.casefold() in _SENSITIVE else sanitize_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


class RawPayloadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str
    dataset: str
    capability: str
    request_id: str
    ingestion_batch_id: str | None = None
    payload: Any
    captured_at: datetime
    payload_hash: str
    status: str

    @classmethod
    def from_payload(
        cls,
        provider: str,
        dataset: str,
        capability: str,
        request_id: str,
        payload: Any,
        captured_at: datetime,
        ingestion_batch_id: str | None = None,
    ) -> "RawPayloadRecord":
        safe = sanitize_payload(payload)
        canonical = json.dumps(safe, sort_keys=True, separators=(",", ":"), default=str).encode()
        return cls(
            provider=provider,
            dataset=dataset,
            capability=capability,
            request_id=request_id,
            ingestion_batch_id=ingestion_batch_id,
            payload=safe,
            captured_at=captured_at,
            payload_hash=hashlib.sha256(canonical).hexdigest(),
            status="NORMALIZED",
        )
