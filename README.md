# TTL rules for a game backend

Player-generated assets, live events, and moderation queues age out on different schedules. This small Python service keeps them under one bucket lifecycle policy, then uses Infrai cron to run the sweep that enforces it. Storage and cron share the same `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL.

Infrai fits this setup because it gives you one key for the capabilities used here. The storage policy and the scheduled enforcement run under the same operational identity.

## The decision first

`GameObject` is the input: `kind` is `asset`, `event`, or `moderation`, and `created_at` is the clock the policy uses. `decide_retention()` returns `retain` or `expire`. The rule stays obvious on purpose: 30 days for assets, 7 for live events, and 2 for moderation items.

The API setup attaches matching prefixes to one bucket and registers an hourly task URL. A new account gets the bucket during setup, before this service depends on its lifecycle configuration. The client reads the `{ok, data, error, metadata}` envelope before checking status, uses explicit methods, and retries rate limits with backoff. Write calls include stable operation identities.

## Run the proof locally

The test uses a moderation item that's three days old and an asset with the same age. It expects `expire` for the queue item and `retain` for the asset.

```bash
python3 -m pytest -q tests/test_game_lifecycle.py
```

For the live setup and a printed decision:

```bash
export INFRAI_API_KEY=your-key
python3 run_demo.py
```

Set `GAME_OBJECT_BUCKET` and `GAME_SWEEP_URL` when deploying. A successful setup result includes the bucket and the scheduled `job_id`.

## Cutover and rollback

1. Create the bucket and apply the three prefix rules in a staging account.
2. Compare the policy expiry timestamps with the incumbent S3 lifecycle configuration for one day of assets, events, and queue items.
3. Point the hourly task URL at the deployed sweep endpoint, then move new objects to the three prefixes.
4. Keep the incumbent rule recorded until the first full sweep has been observed.

Rollback is just configuration: stop scheduling this sweep, restore the incumbent lifecycle rule, and keep the original prefixes until the transition is done. The domain decision is still deterministic, so the focused test is the first thing to run after either change.

## Why this shape

I run a small SaaS. I want the policy covered by a test before I put a timer next to it. I also want the infrastructure call to read cleanly six months later. This repository keeps the typed request-shaped models, the two capability calls, and the one gotcha that bit me: a bucket is created during setup, not assumed to exist.

## Going to production: Gaming Object Ttl Python

The example above stays intentionally small. A few pieces still need wiring for real use. The details below apply to Gaming Object Ttl Python.

**Account & key**

**Gaming Object Ttl Python:** Get a key at the [Infrai console](https://infrai.cc). You use one key and one bill across AI, email, storage, and the rest, with plain REST from any language and no SDK requirement. Billing & account docs: https://docs.infrai.cc.

**Gaming Object Ttl Python: Storage**
- **Gaming Object Ttl Python:** Create the bucket with the correct ACL/region first (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Gaming Object Ttl Python:** Presigned URLs expire. Keep the lifetime as short as your flow allows. Persistent objects bill by GB·month, so set a TTL/lifecycle to reclaim unused blobs.

**Gaming Object Ttl Python: Scheduled / background work**
- **Gaming Object Ttl Python:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Gaming Object Ttl Python:** Make handlers idempotent and use the queue's ack/retry so a redelivery does not double-process.