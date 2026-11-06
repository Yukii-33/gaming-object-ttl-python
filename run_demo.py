import os

from src.game_lifecycle import configure_policy, decide_retention, demo_object
from src.infrai_client import InfraiClient


def main() -> None:
    client = InfraiClient()
    bucket = os.environ.get("GAME_OBJECT_BUCKET", "game-throwaways")
    sweep_url = os.environ.get("GAME_SWEEP_URL", "https://example.com/game-lifecycle-sweep")
    job_id = None
    try:
        setup = configure_policy(client, bucket, sweep_url)
        job_id = setup.get("job_id") if isinstance(setup, dict) else None
        obj = demo_object()
        decision = decide_retention(obj, obj.created_at)
        print({"setup": setup, "object_id": obj.object_id, "action": decision.action, "ttl_days": decision.ttl_days})
    finally:
        if job_id is not None:
            client.delete_cron(str(job_id))
        client.delete_bucket(bucket)


if __name__ == "__main__":
    main()
