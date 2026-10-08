# Validation Reflection — Avni Wadhwani

---

## 1. Prompting notes (Step 3)

**Tool tested:** Gemini
**Transcript:** `../transcripts/gemini_outputs.md`

*Surprises while testing (what the tool did that you did not expect):*

- **It approved its own fake.** IMG-F was generated with Gemini — and in F1 Gemini approved that same AI-generated photo at **100% confidence**. The tool that made the fake could not recognise it.
- **It never actually looked at the photo in F1.** The reasoning says only that *"required photos were attached to support the damage claim"* — the presence of a photo was treated as proof. It missed the heavy wear that contradicts "ripped on day one", which other tools caught.
- **Certainty everywhere.** 100% confidence on 5 of 6 runs, including three wrong decisions (E1, F1, F2), and *"Missing information: none"* on the ambiguous E1 case.
- **It read the customer's words, not the evidence.** In E1 run 2 the reasoning never mentions the photo — the denial rests entirely on the customer's note (*"worn out already after a few weeks"*).
- **It denied for missing evidence while naming the evidence (F2).** It listed *"A photo of the damaged/defective sneakers"* as missing information and still denied at 100% instead of asking for it.
- **It invented a rule about authority (F3).** It told the new team member to *"proceed directly with sending the standard denial email… without needing further manager approval"*, reasoning that only high-value refunds need escalation — treating the absence of a rule as permission.

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

![ReturnGuard storyboard: a damaged-sneakers return moving through customer submission, data check, policy RAG, image and behavior analysis, AI decision and critic, the human governance gate, and the final decision with an audit log](../../proposal/storyboard.png)

*Class-generated storyboard: a "damaged sneakers" return moving through ReturnGuard. AI can
recommend approval; every denial requires human review.*

---

## 4. One finding that changed (or confirmed) my assumption about the proposed scenario (Step 10)

*Tie it to complementarity, trust calibration, shared mental models, or a cognitive pillar
(reasoning / memory / attention) from Gonzalez et al. (2026).*
