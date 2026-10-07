# Validation Reflection — Trupti Reddy

---

## 1. Prompting notes (Step 3)

**Tool tested:** Claude (claude.ai)
**Transcript:** `../transcripts/claude_outputs.md`

*Surprises while testing (what the tool did that you did not expect):*

- **It behaved like an investigator, not a decider.** Almost every "Missing information" field became a list of requests — size tags, box labels, carrier tracking records, close-ups, even photo metadata — far beyond what the format asked for.
- **It questioned the inputs themselves.** In E1 run 1 it said the two images *"appear to be in the opposite order from how they are labeled"*; in run 2 it spotted different laces between the photos and wear too heavy for three weeks. No other tool noticed these.
- **It came closest to catching the fake photo (F1).** It said the photo *"looks like a stock or staged street image"* and asked whether it was original — the only tool to doubt the photo itself, though it never said "AI-generated".
- **Its decision field contradicted its own reasoning.** In F2 the reasoning said the case should be *"not approved until a photo is supplied"* and the customer invited to resubmit — but the decision field said **DENY**. In E1 it raised three reasons for doubt and still denied. A system that reads only the label would act on the wrong thing.
- **It wrote an essay for the authority question (F3).** It said *"I don't know whether ShopCo requires a human to review or sign off on denials"* and told the new team member to check with their lead — the best answer of the four tools — but then suggested goodwill exceptions that aren't in the policy and ended *"the email is fine to send"*.
- **It assumed the customer's gender.** In F2 it wrote *"Her clean history"* about Grace Kim — a gender guessed from a name, which is a small but real bias signal for a system that judges customers.

---

## 2. Speed-dating interview notes (Step 4)

Anonymous — no names or contact details. If a dimension did not come up or does not apply,
write one sentence explaining why.

### P1

| Field | Notes |
|---|---|
| Who | Customer — (e.g. student, shops online monthly) |
| Date / format | |
| First reaction to the concept | |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | | |
| Reliability & consistency | | |
| Latency & performance | | |
| UX friction (human–AI teaming) | | |
| Safety & guardrails | | |
| Cost & efficiency | | |

**Who should have the final say (their answer):**

**Most surprising thing they said:**

### P2

| Field | Notes |
|---|---|
| Who | Reviewer-like — (e.g. part-time retail associate) |
| Date / format | |
| First reaction to the concept | |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | | |
| Reliability & consistency | | |
| Latency & performance | | |
| UX friction (human–AI teaming) | | |
| Safety & guardrails | | |
| Cost & efficiency | | |

**Who should have the final say (their answer):**

**Most surprising thing they said:**

---

## 3. Class-generated storyboard (Step 10)

*Add the storyboard here.*

---

## 4. One finding that changed (or confirmed) my assumption about the proposed scenario (Step 10)

*Tie it to complementarity, trust calibration, shared mental models, or a cognitive pillar
(reasoning / memory / attention) from Gonzalez et al. (2026).*
