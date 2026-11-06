# CP3 demo and submission runbook

Verification already performed: [fresh-source install, real provider checks and tests](evaluation/CP3_VERIFICATION.md).
Forum text is prepared in [submission draft](forum-post.md). Independent teammate and
presenter tasks remain unchecked below.

## Before rehearsal

Follow `app/INSTALL.md` on a fresh clone with local Postgres and synthetic seed data.
A teammate must perform the clean-machine check independently: record OS, Docker version,
commit SHA, commands and any failures below. The current developer machine is not a
clean-machine verification. Never reset the shared Neon database for rehearsal.

- [ ] Teammate / OS / commit: pending
- [ ] `make env`, configure Groq, `make up`, `make migrate`, `make seed`
- [ ] Customer, reviewer and admin sign in
- [ ] Synthetic return shows model output in reviewer trace
- [ ] Upload and missing-evidence paths work
- [ ] `make check` passes with database tests running

## Timed rehearsal

Target 6 minutes total with at least 3 minutes live. Presentation is maintained separately.

| Live time | Action | Evidence to show |
|---|---|---|
| 0:00–1:15 | Submit a low-value changed-mind return, inspect reviewer case | Policy citations, model source and recommendation, critic, final gate |
| 1:15–2:00 | Submit damage claim without photo | Needs-info response before model judgment |
| 2:00–3:00 | Inspect a late return and complete human review | Code window check, named escalation, denial confirmation and cited clause |
| 3:00–3:45 | Inspect a prepared provider-error case | Job retry/error evidence and human queue with Pipeline error |

Auto-approval requires the admin automation switch on and every gate condition clear.
QA sampling can still route a clean case to a person. Do not promise a specific model
judgment for ambiguous or synthetic photos. Expand Pipeline trace, choose Re-run AI,
and show step events arriving over SSE. On a complete in-window case, the policy step
shows real `search_policy` and `check_return_window` function calls when tools are enabled.
Their underlying operations remain Python code. Show token counts, streamed chunk counts
and estimated cost when prices are configured. Do not claim parallel execution or a
second-provider fallback.

## Provider failure rehearsal

Use a private local database, not the shared demo deployment. Keep a copy of the working
configuration privately. Set `CHAT_API_KEY` to an intentionally invalid nonempty value,
then recreate API and worker with `docker compose up -d --force-recreate api worker`.
Submit a complete in-window changed-mind return so the policy model call actually runs.
An empty key selects RuleSteps and does not demonstrate provider failure.

Watch `docker compose logs -f worker`. SDK retries may precede the job retries (30 seconds,
then 2 minutes). Wake-up/sweep timing may extend the wait. Prepare this case before the
live segment rather than waiting on stage. After three failed job attempts, verify the
case routes to a person as Pipeline error, with no automatic approval or denial. Restore
the real key privately and recreate the services. A reviewer can re-run AI after recovery.
Chat assist has its own fixed fallback reply, which is separate from review recovery.

## Backup and handoff

- [ ] Rehearse against the actual demo environment and record timings
- [ ] Record the working main flow, missing evidence and human review before demo day
- [ ] Record the failure/recovery case after it reaches the queue
- [ ] Hide environment files, provider keys and credentials throughout the recording
- [ ] Save an offline copy and verify playback on the presenting laptop
- [ ] Teammate completes the clean-machine checklist above
- [ ] Human posts the repository link and requested submission materials to the forum

Deadline supplied by the team: Friday, November 6, 2026 at 9:00 AM America/Chicago.
No forum post, recording or teammate verification has been completed by this runbook.

## CP4 evaluation choice

Choose **Track B: algorithmic benchmark**. The existing synthetic cases and backend tests
provide a practical starting point without recruiting participants. Freeze policy,
prompts, model configuration and gate settings before evaluation. Build a held-out set
of eligible, late/final-sale, ambiguous, missing-evidence, injection and provider-failure
cases. Have two team members label expected eligibility and route, resolve disagreements,
and separate prompt-development cases from the held-out set.

Compare RuleSteps with ModelSteps using the same cases. Report routing accuracy,
unsafe auto-approvals, automatic denials (must be zero), escalation rate and reviewer
agreement, with per-category counts and repeated runs for model variability. Report
step latency and observed token counts. Report dollar estimates only when both model
prices are configured, and distinguish them from provider invoices. Include failure cases and small-sample limits. A fairness
benchmark needs a defined population and suitable data, not demographic claims from
synthetic account histories.

## Deferred scope

Playwright `tests/e2e/` and a second review provider remain unimplemented. These are
follow-up work, not completed CP3 features. Google sign-in remains optional after CP3.
The offline bias screen and deterministic masking are implemented, with coverage limits
documented in `docs/safety_privacy.md` and `docs/evaluation/README.md`.
