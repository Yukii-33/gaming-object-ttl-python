from datetime import datetime, timedelta, timezone

from src.game_lifecycle import GameObject, decide_retention, lifecycle_rules


def test_old_moderation_item_expires_before_a_fresh_asset() -> None:
    now = datetime(2026, 1, 31, tzinfo=timezone.utc)
    old_queue_item = GameObject("review-9", "moderation", now - timedelta(days=3))
    fresh_asset = GameObject("skin-9", "asset", now - timedelta(days=3))

    assert decide_retention(old_queue_item, now).action == "expire"
    assert decide_retention(fresh_asset, now).action == "retain"


def test_rules_keep_domain_prefixes_explicit() -> None:
    assert lifecycle_rules() == [
        {"prefix": "asset/", "expire_days": 30},
        {"prefix": "event/", "expire_days": 7},
        {"prefix": "moderation/", "expire_days": 2},
    ]
