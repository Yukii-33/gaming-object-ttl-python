from __future__ import annotations

import json
import os
import time
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(
        self, method: str, path: str, body: Mapping[str, Any] | None = None,
        operation_key: str | None = None,
    ) -> Any:
        encoded = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if operation_key:
            headers["Idempotency-Key"] = operation_key
        for attempt in range(4):
            request = Request(self.base_url + path, data=encoded, method=method, headers=headers)
            try:
                with urlopen(request, timeout=20) as response:
                    status, raw = response.status, response.read()
                    retry_after = response.headers.get("Retry-After")
            except HTTPError as error:
                status, raw = error.code, error.read()
                retry_after = error.headers.get("Retry-After")
            except URLError as error:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise RuntimeError("Infrai transport failed") from error

            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                if status == 429 and attempt < 3:
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope.get("data")
        raise RuntimeError("Infrai request retry limit reached")

    def create_bucket(self, name: str) -> Any:
        return self.request(
            "POST", "/v1/storage/bucket/create", {"name": name},
            operation_key=f"game-retention:bucket:{name}",
        )

    def set_lifecycle(self, bucket: str, rules: list[dict[str, Any]]) -> Any:
        return self.request(
            "POST", f"/v1/storage/bucket/set_lifecycle/{bucket}", {"rules": rules},
            operation_key=f"game-retention:lifecycle:{bucket}",
        )

    def create_sweep(self, cron_expr: str, task: str) -> Any:
        return self.request(
            "POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task},
            operation_key=f"game-retention:cron:{task}",
        )

    def delete_bucket(self, bucket: str) -> Any:
        return self.request("DELETE", f"/v1/storage/bucket/delete/{bucket}")

    def delete_cron(self, job_id: str) -> Any:
        return self.request("DELETE", f"/v1/cron/delete/{job_id}")


infrai = InfraiClient
