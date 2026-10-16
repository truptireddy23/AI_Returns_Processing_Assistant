# Safety & Privacy

How ReturnGuard protects people's data and keeps the AI inside its limits. This document
grows with each milestone; sections marked *(planned)* describe work not built yet.

## Accounts and sessions (built in M2)

| Control | How |
|---|---|
| Passwords | Hashed with Argon2id (`argon2-cffi`); never stored or logged in plain text. |
| Sessions | A random 256-bit token in an `httpOnly`, `SameSite=Lax` cookie. The database stores only its SHA-256 hash, so a database leak doesn't hand out live sessions. Sessions expire after `SESSION_TTL_HOURS` (default 12); signing out deletes the row. |
| HTTPS cookies | `COOKIE_SECURE=true` sends the cookie over HTTPS only. The API refuses to start in production without it. |
| CSRF | Every state-changing request from a signed-in user must send the session's CSRF token in `X-CSRF-Token`. The token is held in browser memory, not storage. |
| Roles | `customer`, `reviewer`, `admin`, checked on the server for every endpoint. Customers see only their own orders. Admins hold every reviewer right. |
| Failed sign-ins | One generic message ("Invalid email or password") whether the email exists, the password is wrong, or the account is disabled; unknown emails still run a password check so timing doesn't reveal which accounts exist. |
| Sign-out | The UI only shows "signed out" once the server confirms it; if the API is unreachable it says so and keeps the user signed in rather than pretending. |
| Audit | Every sign-in and sign-out is written to the append-only audit log. |

## Rate limits (built in M2)

| Limit | Default | Key |
|---|---|---|
| Sign-in attempts | `LOGIN_RATE_LIMIT=10/minute` | Client IP |
| Failed sign-ins | `LOGIN_ACCOUNT_FAILURE_LIMIT=20/hour` | Account email |

Over the limit, the API answers `429 Too Many Requests` with a `Retry-After` header.

**Trust model for the client IP.** The browser only talks to the Next.js server, which
forwards `/api/*` to FastAPI with the caller's address in `X-Forwarded-For`
(`app/frontend/src/app/api/[...path]/route.ts`); Uvicorn reads it with `--proxy-headers`.
A client can put its own `X-Forwarded-For` on the request, and Next.js keeps it, so the
per-IP limit alone can be dodged. That is why failed sign-ins are also limited **per
account**, which no header can change. In production, put a reverse proxy (or load
balancer) in front of Next.js that overwrites `X-Forwarded-For` with the real address.

**Known limitation.** Counters are kept in the API process's memory: correct for the single
API process we run, reset on restart, and not shared between replicas. Running more than
one API replica would need a shared store such as Redis. The per-account limit also means
someone could lock a real user out for up to an hour by failing on purpose; for a
production deployment we'd add a CAPTCHA or email unlock instead of a hard block.

## Data at rest (built in M2)

- The audit log is **append-only**: a database trigger rejects `UPDATE`, `DELETE`, and
  `TRUNCATE` on `audit_log`.
- A database `CHECK` constraint makes an automatic denial impossible: a return can only
  be denied with `decided_by_type = 'person'` (M1).
- A review request must go to a different reviewer from the one who made the denial
  (database `CHECK`).
- Shipping addresses are compared for shared-address checks through a SHA-256
  **fingerprint** of the normalised address, not the raw text.
- Only the last 4 digits of a (mock) card number are stored.
- Demo data and accounts can't be loaded in production: the seed script refuses when
  `ENVIRONMENT=production`.

## Hosted database (Neon)

- Connections to Neon always use TLS (`sslmode=require`, passed to the driver as
  `ssl=require`); the password-based login is SCRAM.
- The app uses Neon's pooled endpoint; migrations use the direct one, and refuse to run
  through the pooler.
- Only synthetic demo data is stored there: invented customers at `example.com`
  addresses, and no real payment details (last 4 digits of test card numbers only).
- Tests never touch it: they run on a separate local database, whatever `app/.env` says.
- Startup logs name the database host and whether it's pooled, never the credentials.

## Secrets

- `app/.env` (and the root `.env` the Neon CLI writes) are git-ignored; only
  `app/.env.example` (no values) is committed. The Neon link file `.neon` is git-ignored
  too.
- Log entries whose keys look like secrets (`password`, `token`, `api_key`,
  `authorization`, `cookie`, …) are redacted before they're written.

## Planned

- *(M3)* Upload handling: file type checked from bytes, size and dimension caps,
  metadata read for the authenticity check, then the image is re-encoded to strip it.
- *(M3)* Rate limits on checkout and return submission.
- *(M5)* Masking customer names, emails, addresses, and gendered words before every
  model call (M8); Langfuse receives masked inputs only.
- *(M5)* Prompt-injection handling: customer text is passed as quoted data; the gate is
  code, so text can't change a route.
- *(M5)* Model fallback, schema validation with one repair, and fail-closed escalation.
