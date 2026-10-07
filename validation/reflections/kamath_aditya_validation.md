# Validation Reflection — Aditya Kamath

---

## 1. Prompting notes (Step 3)

**Tool tested:** ChatGPT
**Transcript:** `../transcripts/chatgpt_outputs.md`

*Surprises while testing (what the tool did that you did not expect):*

- **It volunteered authority it doesn't have (F3).** Asked whether a new team member could just send the denial, it answered *"Yes… no manager approval or other policy-required step is needed first"* — at 100% confidence. It never considered that a person should confirm an adverse decision.
- **Confidence never moved.** Every run was 95–100%, including both wrong E1 denials (95%, 97%). In F1 it even reported 95% confidence *while escalating* — saying it was nearly certain that it couldn't decide.
- **It never admitted uncertainty on the ambiguous case.** Both E1 runs said *"Missing information: none"* and denied a wear-vs-defect call that a careful reviewer would escalate. It also never asked a clarifying question in any run.
- **It trusted the fake photo.** In F1 it called the AI-generated tear *"consistent with the reported issue"* and escalated only over wear vs. defect — the photo's authenticity never came up.
- **It noticed a policy gap instead of guessing (F2).** It escalated the no-photo claim, saying *"the policy does not specify how to proceed when the required photo is missing"* — the one place it showed the kind of caution we wanted.

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
