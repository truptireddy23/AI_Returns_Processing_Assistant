# ReturnGuard — Clickthrough Prototype (v0)

A static HTML/CSS/JavaScript clickthrough of the journeys in [`DESIGN_SPEC.md`](../DESIGN_SPEC.md).
There is no backend: all data is fictional and in memory, and AI results are **simulated** so
the interaction design (decision rights, interrogation, trust cues) can be demoed. Refreshing
the page resets everything.

## How to open it

Serve the repo root with any static server (so the shared test photos load), then open the
prototype:

```bash
python3 -m http.server 8765
```

Then visit <http://localhost:8765/prototype/index.html>. Opening `index.html` directly also
works in most browsers.

Use **View as** in the top bar to switch between Customer, Reviewer, and Admin. The three
roles share the same data — a return submitted as the customer appears in the reviewer queue,
and the reviewer's decision appears on the customer's order.

## Demo script (Slide 6)

1. **Customer — submit a return.** *My orders* → **Return item** on the sneakers → reason
   *Damaged / defective* (the photo field appears) → add a note and a photo → **Submit**.
   Watch the checks run, then the status moves to *Under review* (automation is off).
2. **Reviewer — interrogate the AI.** *View as Reviewer* → the queue's **Why here** column
   shows why each case needs a person. Open **R-216** (possible AI-generated photo): AI label,
   confidence band with "Why not higher", checks, photo signal, cited policy clause and
   version, customer history.
3. **Reviewer — decision rights.** Open **R-211** (AI suggests Deny). Try **Approve** without
   a reason → blocked: disagreeing with the AI needs a reason. Click **Deny…** → the
   confirmation dialog restates the policy basis → **Confirm denial**.
4. **Customer — accountability.** *View as Customer* → *My orders* → the shorts return now
   says it was not approved, why, and that **a person reviewed it**.
5. **Admin — goals and constraints.** *View as Admin* → turn **Automatic approvals** on →
   **Save**. The locked rule ("The AI can never deny a return") is shown, not hidden. The
   reviewer–AI agreement rate updated after step 3.
6. **Customer — automation on.** Add the backpack to the cart → checkout with test card
   `4242 4242 4242 4242` → return it as *Changed my mind* → it is **auto-approved** and skips
   review. Try **R-214** in the queue for contrast: a clean $329 return still needs a person.
7. **Audit log.** Every AI step, gate routing, reviewer decision, and settings change is
   listed, newest first. Filter by case (e.g. `R-211`).

## Seeded cases in the reviewer queue

| Case | Situation | AI suggests | Why here |
|---|---|---|---|
| R-208 | Worn sneakers claimed as defective (IMG-C) | Escalate | Low confidence |
| R-211 | Late return, day 47 (Maya's order) | Deny | Denial |
| R-214 | $329 chair, otherwise clean | Approve | High value |
| R-215 | Damage claimed, no photo | — (stopped at data check) | Missing photo |
| R-216 | Possible AI-generated damage photo (IMG-F) | Escalate | Possible fake photo |

## Files

- `index.html` — page shell
- `styles.css` — IBM Carbon–inspired styles (Gray 10 theme, AI label, data tables, danger modal)
- `app.js` — screens, seeded data, simulated pipeline, governance gate, audit log
