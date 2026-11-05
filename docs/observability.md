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
| *(planned, M5)* What did the models cost and how long did they take? | Langfuse traces and the token/cost columns on `agent_runs` |

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
| `model`, `prompt_version`, `tokens_in`, `tokens_out`, `cost_usd` | Filled once steps call models (M5) |
| `error` | Set if the step failed |

`agent_run_events` records `started` / `finished` events per step for the live trace view
(admin, M8). Until the AI steps exist, the stand-in steps label their output
`"source": "rules"`, and the gate's audit entry records `steps_source`.

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

## *(planned)*

- **M5:** Langfuse Cloud traces for every model call (prompt version, tokens, cost,
  latency, errors), linked to `agent_runs` by `run_id`; masked inputs only.
- **M8:** admin views for the trace, the audit log, escalation rate, agreement with
  reviewers by product type and reason, and cost per decision.
