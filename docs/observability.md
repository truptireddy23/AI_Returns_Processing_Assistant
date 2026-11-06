# Observability

How to see what ReturnGuard is doing, why it decided what it decided, and what went
wrong. This document grows with each milestone; *(planned)* marks what isn't built yet.

## Where to look

| Question | Look at |
|---|---|
| Is the system up? | `GET /api/healthz` (process), `GET /api/readyz` (database reachable, else `503`), the worker's `GET /healthz` on port 8001 (Docker health check), `docker compose ps` |
| What happened to one request? | Structured logs with its `request_id` |
| What did the pipeline do for one return, and why? | `agent_runs` (one row per step) and `agent_run_events` (the timeline) |
| Who did what, when? | `audit_log` (append-only) |
| Is work stuck or failing? | `jobs` (status, attempts, `last_error`, `run_after`) |
| How many tokens did model steps use, and how long did they take? | `agent_runs.tokens_in`, `tokens_out`, `cost_usd` and `latency_ms`; detailed provider usage is also in `output.output`. Cost is a configured estimate, or NULL when unknown. |

## Logs

- **JSON lines** from the API and worker (`structlog`), one event per line, with a UTC
  timestamp, level, logger, and event name (`auth.login`, `return.submitted`,
  `pipeline.decided`, `worker.job_error`, ...).
- **Request IDs.** Every API response carries `X-Request-ID` (taken from the request or
  generated), and every log line written while handling it includes `request_id`, so one
  request can be followed end to end. The signed-in user's ID is added as `user_id`.
- **Secrets are redacted** before writing: any key that looks like a password, token, API
  key, authorization header, or cookie becomes `[redacted]`. Card numbers and CVCs are
  never logged.
- **Startup lines** say which database host (and whether it's the pooled endpoint) and
  which storage backend (`s3` = Neon Object Storage, `local`) the process is using.
- Read them with `docker compose logs -f api worker`.

## The pipeline trace (`agent_runs`, `agent_run_events`)

Every review gets a `run_id`. Each step writes an `agent_runs` row:

| Column | Meaning |
|---|---|
| `step` | `data_check`, `policy`, `image`, `behavior`, `recommendation`, `critic`, `gate` |
| `output` | The step's full result (JSON): e.g. the gate's reasons and evidence strength |
| `input_hash` | SHA-256 of the step's input, so identical inputs can be matched without storing customer text |
| `policy_version` | The policy the step used |
| `latency_ms` | How long the step took |
| `model`, `prompt_version`, `tokens_in`, `tokens_out`, `cost_usd` | Populated for model judgment steps. Cost uses configured input/output USD per million tokens. Missing prices/usage produce NULL, never an assumed zero. Rules and skipped calls keep these fields NULL. |
| `error` | Reserved schema field; exceptions currently appear in worker logs and `jobs.last_error`. A committed start without a finish identifies the interrupted step. |

`agent_run_events` records committed step starts/finishes for the reviewer SSE trace view
(`/api/review/cases/{id}/events`, staff only). The stream reconnects using Last-Event-ID
and exposes safe metadata only, never customer notes or raw model deltas.

Provider JSON replies stream when `CHAT_STREAM_ENABLED=true`; the client assembles and
validates the response before the pipeline uses it. Stream chunk counts and actual policy
tool calls appear in step output and their names in the live trace. Token usage for the
policy step includes its tool rounds and final answer.
 Model-backed results
label their source `model`; deterministic results label it `rules`. The gate audit entry
records `steps_source`. Real inference runs when `CHAT_API_KEY` is configured.

## The audit log (`audit_log`)

Append-only: a database trigger rejects `UPDATE`, `DELETE`, and `TRUNCATE`. One row per
action: who (`actor_type`: customer, reviewer, admin, check, ai, gate, system; and
`actor_user_id` for people), what (`action`), which return, details (JSON), and when.
Current actions include `auth.signup`, `auth.login`, `auth.logout`, `order.placed`,
`return.submitted`, `return.photo_added`, `check.missing_evidence`, `gate.auto_approved`,
`gate.escalated` (with every reason that applied), and `pipeline.failed`.

## Jobs (`jobs`)

| Status | Meaning |
|---|---|
| `queued` | Waiting; `run_after` says when it's due (later for a retry) |
| `running` | Claimed by a worker (`locked_at`); reclaimed if older than 10 minutes |
| `done` | Finished |
| `failed` | Out of attempts (3); the case went to a person as "Pipeline error" |

`attempts` and `last_error` show what went wrong. The worker logs `worker.job_started`,
`worker.job_done`, `jobs.retry_scheduled`, `jobs.reclaimed_stale`, and `jobs.failed`.

## Keeping a scale-to-zero database asleep

Neon suspends the database after 5 minutes without queries, and every query wakes it. So
nothing polls it: the worker is woken over HTTP by the API, its backstop sweep runs every
30 minutes (`WORKER_SWEEP_SECONDS`), and a customer's open status page re-checks with
back-off (1.5 s, growing to 30 s) only while a return is being processed.

## Implemented and deferred

The admin dashboard, trace view, searchable audit log, escalation metrics and reviewer
agreement breakdowns are implemented. Langfuse and Prometheus/Grafana are not integrated.
`agent_runs`, `agent_run_events`, structured logs and the admin dashboard cover current
observability. Set BOTH `CHAT_INPUT_USD_PER_MILLION` and `CHAT_OUTPUT_USD_PER_MILLION` from
your provider's current price for `CHAT_MODEL`. Estimates exclude embeddings, failed
attempts without usage and provider billing adjustments. The database stores six decimal
places, so a very small amount may round to zero. Incomplete usage stays unknown.

Step rows commit as they finish, so partial traces survive a later failure. A start with
no matching finish identifies an interrupted or failed step. Inspect worker logs and
job errors for the exception and retry outcome.
