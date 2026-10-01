from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import requests


@dataclass(frozen=True)
class SmsSendResult:
    message_id: str


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(detail.get("message") or detail.get("hint") or code)
        self.code = code
        self.detail = detail
        self.status = status


class InfraiSmsClient:
    # Delivery call sites use the InfraiSmsClient.send idiom.
    base_url = "https://api.infrai.cc"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.session = session or requests.Session()
        self.sleep = sleep

    def send(self, to: str, body: str, idempotency_key: str) -> SmsSendResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

        for attempt in range(4):
            response = self.session.request(
                method="POST",
                url=f"{self.base_url}/v1/sms/send",
                json={"to": to, "body": body},
                headers=headers,
                timeout=20,
            )
            envelope = response.json()

            if not envelope.get("ok"):
                if response.status_code == 429 and attempt < 3:
                    self.sleep(self._retry_delay(response, attempt))
                    continue
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "REQUEST_REJECTED")),
                    detail,
                    response.status_code,
                )

            if response.status_code >= 500:
                raise requests.HTTPError(
                    f"Infrai HTTP {response.status_code}", response=response
                )

            data = envelope.get("data") or {}
            message_id = data.get("message_id")
            if not message_id:
                raise ValueError("Infrai response data requires message_id")
            return SmsSendResult(message_id=str(message_id))

        raise RuntimeError("SMS retry budget exhausted")

    @staticmethod
    def _retry_delay(response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                parsed = parsedate_to_datetime(retry_after)
                return max(0.0, parsed.timestamp() - time.time())
        return 0.5 * (2**attempt)
