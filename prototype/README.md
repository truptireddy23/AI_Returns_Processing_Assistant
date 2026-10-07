# ReturnGuard — Clickthrough Prototype (v1)

A static HTML/CSS/JavaScript clickthrough of the journeys in [`DESIGN_SPEC.md`](../DESIGN_SPEC.md)
(v1). There is no backend: all data is fictional and in memory, and AI results are
**simulated** so the interaction design — decision rights, interrogation, and trust cues — can
be demoed. Refreshing the page resets everything.

## How to open it

Serve the repo root with any static server (so the shared test photos load), then open the
prototype:

```bash
python3 -m http.server 8765
```

Then visit <http://localhost:8765/prototype/index.html>.

Use **View as** in the top bar to switch between Customer, Reviewer, and Admin. The three
roles share the same data — a return submitted as the customer appears in the reviewer
queue, and the reviewer's decision appears on the customer's order.

## What changed from v0 (and why)

| v0 | v1 | Evidence | Feature |
|---|---|---|---|
| Model confidence shown as a percentage | **Evidence strength** (Strong / Mixed / Weak) computed from the checks, plus **"Uncertain about"** | Tools were 95–100% confident on wrong answers; interviewees distrust "100%" and would ignore "95%" | M3 |
| One "signal only" photo line | Separate **photo match** and **photo authenticity** checks; an **Unverified photo** banner | 0 of 4 tools detected the AI-generated photo | M5 |
| Incomplete returns went to reviewers | **Waiting on customer** — the rule-based data check asks for the missing photo; these never reach the queue | Two tools denied a claim for a missing photo | M6 |
| "Why here" included "Low confidence" | **Named reasons only:** proposed denial, unverified photo, ambiguous call, high value, elevated risk, automation off, customer review | Reviewer: *"filter cases intelligently rather than just passing its uncertainty to employees"* | M2 |
| No ambiguity handling | **Ambiguous call** banner; these cases always go to a person | 3 of 4 tools denied the wear-vs-defect case | M4 |
| No way to challenge a denial | **Request a review** on the customer's denial; shown to the reviewer as a banner | Customer raised appeals unprompted | S2 |
| Single agreement number | Agreement **by product type**, **overrides by reason**, and **escalation rate** | Reviewer asked for override tracking | S1 |

## Demo script (Slide 6)

1. **Reviewer — why is this case here?** *View as Reviewer.* Every row has an **Evidence**
   strength and one named **Why here** reason. Switch the filter to **Waiting on customer**:
   R-215 (no photo) never reached the queue.
2. **Reviewer — an unverified photo.** Open **R-216**: the *Unverified photo* banner comes
   first, evidence is *Weak (3 of 6 checks clear)*, and the authenticity check is its own row.
   No percentage anywhere.
3. **Reviewer — an ambiguous call.** Open **R-208**: the *Ambiguous call* banner (wear vs.
   defect) explains why a person must decide.
4. **Reviewer — decision rights.** Open **R-211** (AI suggests Deny). Try **Approve** without
   a reason → blocked. Click **Deny…** → the dialog restates the policy basis and tells you
   the customer can request a review → **Confirm denial**.
5. **Customer — accountability and appeal.** *View as Customer* → *My orders* → the shorts
   return shows the policy rule, the evidence considered, and that a person reviewed it.
   Click **Request a review**, explain, and send.
6. **Reviewer — the review comes back.** R-211 is back in the queue as *Customer review*, with
   the customer's explanation as a banner on the case page.
7. **Admin — goals and constraints.** *View as Admin*: the three fixed rules, the escalation
   rate, agreement by product type, and overrides by reason. Turn **Automatic approvals** on
   → **Save**.
8. **Customer — automation on.** Return the sneakers as *Damaged / defective* with a photo →
   every check clears → **auto-approved**, skipping review. R-214 ($329) still needs a person.
9. **Audit log.** Every rule check, AI step, gate reason, human decision, customer request,
   and settings change, newest first. Filter by case (e.g. `R-211`).

## Seeded cases

| Case | Situation | AI suggests | Evidence | Why here |
|---|---|---|---|---|
| R-208 | Worn sneakers claimed as defective (IMG-C) | Escalate | Mixed | Ambiguous call |
| R-211 | Late return, day 47 (Maya's order) | Deny | Strong | Proposed denial |
| R-214 | $329 chair, otherwise clean | Approve | Strong | High value |
| R-215 | Damage claimed, no photo | — | Not assessed | Missing evidence (waiting on customer) |
| R-216 | Possible AI-generated damage photo (IMG-F) | Escalate | Weak | Unverified photo |

## Files

- `index.html` — page shell
- `styles.css` — IBM Carbon–inspired styles (Gray 10 theme, AI label, tags, data tables, danger modal)
- `app.js` — screens, seeded data, simulated pipeline, evidence strength, governance gate, audit log
