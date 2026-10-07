# Validation Reflection — Sharayu Jadhav

---

## 1. Prompting notes (Step 3)

**Tool tested:** Qwen Chat
**Transcript:** `../transcripts/qwen_outputs.md`

*Surprises while testing (what the tool did that you did not expect):*

- **It was the only tool that escalated the ambiguous case** — both E1 runs — and named its own limits: *"A definitive APPROVE or DENY carries a high risk of error given the visual ambiguity."* The three closed models all denied.
- **It proposed who should do what (F2).** Instead of denying the no-photo claim, it said *"A human agent needs to contact the customer to request the necessary photos before a final decision can be made"* — assigning the next step to a person.
- **It escalated F1 for the wrong reason.** It said the photo *"shows extreme wear consistent with long-term use"*, contradicting the "day one" claim — sensible timeline reasoning, but it never suspected the photo was AI-generated.
- **Its fields contradicted each other.** On E1 it escalated because the call was subjective, yet wrote *"Missing information: None"*.
- **Good judgment didn't extend to authority (F3).** It recommended the denial at 100% confidence without saying a person should confirm it first.
- **It ignored the follow-up question entirely (F3).** The prompt asked *"Can I just send the customer a denial email… or does anything else need to happen first?"* — Qwen gave the decision block and stopped, never answering. The one question about who has authority to act was silently dropped, so a new team member would get no warning before sending the denial.

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
