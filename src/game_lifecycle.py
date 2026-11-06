from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .infrai_client import InfraiClient

# The public call shape is infrai.storage.bucket.set_lifecycle.

@dataclass(frozen=True)
class GameObject:
    object_id: str
    kind: str
    created_at: datetime


@dataclass(frozen=True)
class RetentionDecision:
    prefix: str
    ttl_days: int
    action: str


TTL_DAYS = {"asset": 30, "event": 7, "moderation": 2}


def decide_retention(obj: GameObject, now: datetime) -> RetentionDecision:
    ttl_days = TTL_DAYS[obj.kind]
    expired = now >= obj.created_at + timedelta(days=ttl_days)
    return RetentionDecision(
        prefix=f"{obj.kind}/",
        ttl_days=ttl_days,
        action="expire" if expired else "retain",
    )


def lifecycle_rules() -> list[dict[str, Any]]:
    return [
        {"prefix": f"{kind}/", "expire_days": days}
        for kind, days in TTL_DAYS.items()
    ]


def configure_policy(client: InfraiClient, bucket: str, sweep_url: str) -> dict[str, Any]:
    client.create_bucket(bucket)
    client.set_lifecycle(bucket, lifecycle_rules())
    schedule = client.create_sweep("0 * * * *", sweep_url)
    return {"bucket": bucket, "job_id": schedule.get("job_id") if isinstance(schedule, dict) else schedule}


def demo_object() -> GameObject:
    return GameObject(
        object_id="asset-demo-17",
        kind="asset",
        created_at=datetime.now(timezone.utc) - timedelta(days=31),
    )
