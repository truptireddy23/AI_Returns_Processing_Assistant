# Opportunity Framing

What we will build, and why — prioritised from the prompting study (`transcripts/`), the
speed-dating interviews (`reflections/`), the gap analysis (`GAP_ANALYSIS.md`), and the
complementarity lens (`THEORY_LENS.md`, Gonzalez et al., 2026).

---

## 1. The opportunity

Today's AI assistants can already apply a return policy quickly and consistently — every
tool got the clear case and the date arithmetic right. What they cannot do is know when
they should **not** decide: they denied ambiguous cases with near-certainty, accepted a fake
photo as proof, and told a new team member to send a denial with no human check.
Customers and retail staff both want AI to handle the routine work, but they want a person
to own denials and judgment calls, and they want to see the evidence rather than a score.

**ReturnGuard's opportunity is not a better fraud score. It is a system that decides who
should decide** — routing clear cases to the AI and judgment, authenticity, and denials to
a person, with the evidence that person needs to act in under a minute.

---

## 2. Hypothesis evolution — what we thought vs. what we found

| # | We thought… | …but the evidence showed | Source |
|---|---|---|---|
| 1 | A **confidence score** would help reviewers and customers trust the AI | Confidence didn't track correctness (95–100% on wrong answers), and people distrust it: *"Claiming 100% makes me wonder whether the AI understands its own limitations"*; a retail associate would *"probably ignore a score like '95%'"* | E1, F1, F2; P1 (C7); P2 (R10) |
| 2 | **Escalating anything uncertain** was the safe default | Over-escalation is its own failure: *"The system should filter cases intelligently rather than just passing its uncertainty to employees."* Escalation must be for specific reasons | P2 (R16) |
| 3 | AI **photo analysis** could screen damage claims | 0 of 4 tools detected an AI-generated photo; Gemini approved its own fake at 100%. Photo checks are signals that need an authenticity layer and a human | F1 |
| 4 | "AI never denies" was a **sensible guardrail** to add | It is the core requirement: 0 of 4 tools said a human must confirm a denial, and two said to send it without approval. It must be enforced by the system, not trusted to the model | F3; P1 (C12); P2 (R7, R17) |
| 5 | **Appeals** could wait until a later version | A customer raised appeals unprompted, twice: *"There should be an easy way for customers to appeal."* A minimal request-a-review is needed now | P1 (C15, C16) |
| 6 | Customers mainly want **speed** | Customers would wait for accuracy: *"I'd choose the human review"* over a fast decision that might be wrong | P1 (C10, C13) |
| 7 | AI's risk was **inconsistency** | Each tool was consistent run to run — consistently wrong on E1. Humans are the inconsistent ones on borderline cases (*"Experience level… can affect the outcome"*). AI should own consistent rule checks; humans own judgment | E1 runs 1–2; P2 (R12) |
| 8 | The big **closed models** would perform best | The open-weight model (Qwen) was the only one to escalate the ambiguous case — relevant to choosing the model for our build | E1 |

---

## 3. Prioritised feature matrix

**How we prioritised**
- **Must:** prevents a complementarity break seen in *both* the prompting study and the
  interviews.
- **Should:** addresses a break seen in one source.
- **Could:** worthwhile, weaker evidence.

Every feature is justified as **evidence → complementarity break → principle** (Gonzalez et
al., 2026), not by "users liked it".

### Must have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| M1 | **Human-only denials** — the gate cannot finalise a denial; a reviewer confirms in a dialog that restates the policy basis; the customer is told a person reviewed it | F3 (0 of 4 tools required human sign-off; ChatGPT: *"no manager approval… is needed"*) and the interviews (P1: *"a denial should go to a human"*; P2: *"I wouldn't want the AI to have authority to deny someone without human oversight"*) show a **role-partition break** — the AI claims decision rights it should not hold. **Role partitioning; goals & constraints** ("circuit breakers requiring human review"). |
| M2 | **Governance gate with named escalation reasons** — ambiguity, missing evidence, unverified photo, high value, proposed denial; the review queue shows the reason | P2 (*"filter cases intelligently rather than just passing its uncertainty to employees"*) and E1 (tools forced yes/no answers on ambiguity) show an **attention-orchestration break** — either the AI decides what it shouldn't, or it floods the human. **Attention & interrogation orchestration** (escalation protocols). |
| M3 | **Evidence strength instead of self-rated confidence** — computed from the checks, with a "Why not higher" list | E1/F1/F2 (95–100% on wrong answers) and P1/P2 (100% *lowers* trust; "95%" would be ignored) show a **trust-calibration break**. **Attention & interrogation orchestration** (confidence thresholds the human can interrogate). |
| M4 | **Ambiguity flag** — when the policy hinges on judgment (wear vs. defect), the gate always escalates | E1 (3 of 4 tools denied at 70–100%) and P2 (*"High confidence shouldn't override obvious ambiguity"*; their hardest real case is wear vs. defect) show a **reasoning break** on judgment calls. **Role partitioning** (humans own ambiguous calls). |
| M5 | **Photo authenticity check** with an explicit "not verified" state; unverified damage photos are never auto-approved | F1 (0 of 4 detected the fake; Gemini approved its own at 100%) and P2 (*"I'd also want the system to flag suspicious images instead of assuming every uploaded photo is genuine"*) show an **attention break** — AI misses unknown unknowns. **Attention orchestration; knowledge infrastructure** (provenance). |
| M6 | **Rule-based data check before any AI step** — missing evidence routes to "ask the customer", never to a decision | F2 (Claude and Gemini denied for a *missing* photo; Claude's label contradicted its reasoning) and P1 (*"the customer could have additional context that the AI doesn't understand"*) show a **memory / error-detection break**. **Goals & constraints** (guardrails encoded outside the model). |
| M7 | **Policy clause and version cited on every finding** | P1 (*"Showing me the exact policy rule would make the decision feel more legitimate"*), P2 (wants *"the exact policy rule the AI is using"*), and F3 (Gemini invented a rule about approvals) show a **shared-mental-model break** when provenance is missing. **Knowledge infrastructure** (transparent, auditable provenance). |

### Should have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| S1 | **Override reasons and agreement tracking** — overriding the AI requires a short reason; agreement is broken down by product type and reason | P2 (*"track when employees override the AI, because those overrides could reveal where the AI isn't working well"*) shows the system cannot improve without a **feedback loop**. **Training & evaluation** (learning from errors, after-action review). |
| S2 | **Customer "request a review"** on a denied return, routed to a reviewer | P1 (*"There should be an easy way for customers to appeal"*; a past denial for "signs of use" felt unfair because *"I didn't really have a way to challenge their assessment"*) shows an **accountability break**. **Meta-coordination** (humans manage exceptions). |
| S3 | **Customer-facing explanation** — plain-English reason, the policy rule applied, and the evidence considered | P1 (wants the return date, reason, photos, and damage assessment the AI considered) shows a **trust-calibration break** on the customer side. **Knowledge infrastructure** (collaborative artifacts). |
| S4 | **Admin automation switch and thresholds** — automation off by default; an admin turns it on with evidence | P1 (*comfortable with AI handling straightforward cases*) and P2 (wants time saved on easy approvals) support automation only within **human-set limits**. **Goals & constraints.** |

### Could have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| C1 | **Strip names and gendered cues** from model inputs | Claude assumed a customer's gender from their name (*"Her clean history"*, F2) — a **reasoning / bias-detection risk**. **Reasoning** (humans adjudicate fairness; AI inputs minimised). |
| C2 | **Full audit log** of every AI step and human action | Supports S1 and accountability (P1 blamed the store for unsafe reliance on AI). **Knowledge infrastructure** (audit trails). Single-source evidence, so lower priority as a *visible* feature — it is still built underneath M1–S4. |

### Not now (and why)

Multiple automation levels, fraud-ring visualisation, and an analytics dashboard beyond the
agreement rate: no prompting or interview evidence pointed to them, so they would be
features justified only by assumption.

---

## 4. How this changes the design

The Must and Should features are carried into `DESIGN_SPEC.md` v1. Compared with v0, the
evidence **adds** M2's named escalation reasons, M3's evidence strength, M4's ambiguity
flag, M5's photo authenticity check, M6's pre-AI data check, S1's breakdown of overrides,
and S2's request-a-review; and **confirms** M1 (human-only denials) and M7 (policy
provenance), which v0 already had.
