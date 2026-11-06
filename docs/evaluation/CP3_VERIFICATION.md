# CP3 implementation verification

Performed November 5, 2026 (America/Chicago). Presentation files were excluded.

## Automated checks

`make check` passed backend/frontend lint, backend/frontend type checks and all 309
backend tests with local Postgres. New tests cover input masking, group-risk screens,
model usage and cost persistence, tool allowlists/arguments, provider-stream assembly,
missing usage, SSE role checks and cursor resumption. Existing tests cover retries,
human-only denials, reviewer re-runs and the primary API flows.

Docker builds of API, worker and the production Next.js frontend completed from a fresh
source copy. No existing host virtualenv or node_modules entered that copy. Docker build
caches were allowed. The stack used a new Compose project and a new Postgres volume,
local photo storage, blank hosted DB/storage credentials, and alternate loopback ports
(33000 web, 38000 API, 55432 DB) to avoid the developer stack. All containers became
healthy. Migrations 0001–0006 and demo seeding succeeded.

This is an automated fresh-source/fresh-database check on the developer's machine,
not independent verification by a teammate on another machine.

## Live provider and recovery checks

- Direct Groq Qwen `qwen/qwen3.8-27b` probe executed both policy function tools and returned
  streamed JSON. A later full-flow run reached that model's daily token quota.
- The quota failure exhausted three job attempts and routed to a human as Pipeline error,
  without a final decision. The HTTP recovery smoke check passed, including a separate
  missing-photo case that reached `needs_info`.
- For the successful full workflow, the isolated stack used Groq `openai/gpt-oss-20b`
  with low reasoning effort. The repository's normal model configuration was unchanged.
  Customer signup, test-card checkout, return submission, real policy/recommendation/
  critic calls, both policy tools, human escalation and missing-evidence recovery passed.
- Authenticated reviewer SSE delivered the trace through the Next.js proxy. A live AI
  re-run delivered starts and finishes across successive stream updates and kept the
  case `under_review` with `final_decision = null`.
- Dedicated model/token/prompt-version/cost columns populated in Postgres. The policy
  step recorded 2,189 input and 100 output tokens across tool rounds and final answer.
  Its estimated cost persisted as $0.000194 at the database's six-decimal precision.
  Test rates were $0.075 input and $0.30 output per million tokens, from
  [Groq's published GPT-OSS 20B pricing](https://console.groq.com/docs/models).
- The synthetic name and email inserted in the return note did not appear in that case's
  stored model-step outputs. Original notes intentionally remain in the application DB.
- The paired synthetic behavior audit ran and produced the committed JSON report.
  Both groups had four profiles and equal risk-pass rates. The report marks both samples
  small and does not claim demographic fairness.

The successful smoke case required no photo model call. It does not validate vision
accuracy or claim that GPT-OSS 20B supports photo inputs. The network/provider checks
are point-in-time evidence, not a guarantee that tomorrow's quota is sufficient.

## Reproduce

From `app/`, against a private local database:

```bash
make env
# Configure model key, endpoint, model and optional USD token prices privately.
make up
make migrate
make seed
make check
make bias-audit
make smoke
make smoke SMOKE_ARGS='--live --timeout 300'
```

`make smoke` is read-only by default. `--live` creates synthetic accounts, purchases and
returns and invokes the provider. It requires seeded reviewer credentials and both policy
tools enabled. Never point it at a shared demo database. For the explicit failure check,
use a nonempty invalid key on the private local stack, recreate API/worker, and run:

```bash
make smoke SMOKE_ARGS='--live --expect-failure --timeout 300'
```

The isolated verification used shorter job backoff (1 and 2 seconds) and no SDK retries
to exercise failure recovery promptly. Normal defaults remain 30/120 seconds plus SDK
retry behavior. Real quota exhaustion, rather than an invalid key, triggered the verified
failure path.

## Still requires people or external access

- Teammate installation on a separate machine.
- Timed presentation rehearsal and a backup screen recording. Browser automation could
  not attach to the local page in this session, so no visual walkthrough or recording
  is claimed.
- Course forum submission: destination and access have not been supplied.
