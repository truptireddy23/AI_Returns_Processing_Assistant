# Opportunity Framing

What we will build, and why — prioritised from the prompting study (`transcripts/`), the eight
speed-dating interviews (`reflections/`), the gap analysis (`GAP_ANALYSIS.md`), and the
complementarity lens (`THEORY_LENS.md`, Gonzalez et al., 2026).

**How sources are cited:** prompting scenarios by ID (T1, E1, F1–F3, see
`PROMPTING_PROTOCOL.md`); interviews by member and interviewee — e.g. *Aditya P1* is Aditya's
customer, *Trupti P2* is Trupti's reviewer-like interviewee. Counts come from the
"Across all eight interviews" table in `GAP_ANALYSIS.md` and only include people who were asked.

---

## 1. The opportunity

Today's AI assistants can already apply a return policy quickly and consistently — every
tool got the clear case and the date arithmetic right. What they cannot do is know when they
should **not** decide: they denied an ambiguous case with near-certainty, accepted a fake
photo as proof, and told a new team member to send a denial with no human check. Customers
and retail staff want AI to handle the routine work — but 7 of 8 interviewees said a person
must make denials, and all 7 asked about confidence scores wanted the reason and the
uncertainty instead of a number.

**ReturnGuard's opportunity is not a better fraud score. It is a system that decides who
should decide** — routing clear cases to the AI and judgment, authenticity, and denials to a
person, with the evidence that person needs to act in under a minute.

---

## 2. Hypothesis evolution — what we thought vs. what we found

| # | We thought… | …but the evidence showed | Source |
|---|---|---|---|
| 1 | A **confidence score** would help reviewers and customers trust the AI | Confidence didn't track correctness (95–100% on wrong answers), and **7 of 7** interviewees asked distrusted a bare score: *"Claiming 100% makes me wonder whether the AI understands its own limitations"*; *"Percentages can make people lazy and trick them into hitting 'approve' without actually looking"* | E1, F1, F2; Aditya P1, P2; Sharayu P1, P2; Trupti P1, P2; Avni P2 |
| 2 | **Escalating anything uncertain** was the safe default | Over-escalation is its own failure: *"The system should filter cases intelligently rather than just passing its uncertainty to employees"*; *"If everything is 'needs review' in December, I'm back to doing it all by hand."* Escalation must be for specific reasons | Aditya P2; Trupti P2 |
| 3 | AI **photo analysis** could screen damage claims | 0 of 4 tools detected an AI-generated photo; Gemini approved its own fake at 100%. Meanwhile **3 of 3** reviewer-like interviewees asked already use concrete fake-photo heuristics, and *"A photo shows you an angle, not the shoe."* Photo checks are signals that need an authenticity layer and a human | F1; Aditya P2; Sharayu P2; Trupti P2 |
| 4 | "AI never denies" was a **sensible guardrail** to add | It is the core requirement: 0 of 4 tools said a human must confirm a denial, and two said to send it without approval — while **4 of 4** reviewer-like interviewees would not send that denial. It must be enforced by the system, not trusted to the model | F3; Aditya P2; Sharayu P2; Trupti P2; Avni P2 |
| 5 | **Appeals** could wait until a later version | Customers asked for a way to challenge decisions unprompted, and **4 of 4** had a past return outcome that felt unexplained or weakly evidenced: *"There should be an easy way for customers to appeal"* | Aditya P1; Sharayu P1; Trupti P1; Avni P1 |
| 6 | Customers mainly want **speed** | **3 of 3** customers asked would accept a slower decision if a person checks it — for unclear or adverse cases: *"I'd choose the human review"*; *"Check the hard ones, not all of them"* | Aditya P1; Sharayu P1; Trupti P1 |
| 7 | AI's risk was **inconsistency** | Each tool was consistent run to run — consistently wrong on E1. Humans are the inconsistent ones on borderline cases: *"Two of us can grade the same shoe a B and a C."* AI should own consistent rule checks; humans own judgment | E1 runs 1–2; Aditya P2; Sharayu P2; Trupti P2 |
| 8 | The big **closed models** would perform best | The open-weight model (Qwen) was the only one to escalate the ambiguous case — relevant to choosing the model for our build | E1 |
| 9 | A reviewer just needs the AI's **recommendation** | Reviewers need to know *where to look*, and fast recommendations risk rubber-stamping: *"Show me where to look — I'll tell you if it's right"*; the role shifts *"from 'decision-maker' to 'validator'"*; *"If my name is on the denial, I need to have actually looked"* | Aditya P2; Sharayu P2; Trupti P2 |

---

## 3. Prioritised feature matrix

**How we prioritised**
- **Must:** prevents a complementarity break seen in *both* the prompting study and the
  interviews.
- **Should:** addresses a break seen in one source (usually several interviews).
- **Could:** worthwhile, weaker evidence.

Every feature is justified as **evidence → complementarity break → principle** (Gonzalez et
al., 2026), not by "users liked it".

### Must have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| M1 | **Human-only denials** — the gate cannot finalise a denial; a reviewer confirms in a dialog that restates the policy basis; the customer is told a person reviewed it | F3 (0 of 4 tools required human sign-off; ChatGPT: *"no manager approval… is needed"*) and **7 of 8** interviewees (*"The AI can say yes. Only a person gets to say no"* — Trupti P1) show a **role-partition break** — the AI claims decision rights it should not hold. **Role partitioning; goals & constraints** ("circuit breakers requiring human review"). |
| M2 | **Governance gate with named escalation reasons** — ambiguity, missing evidence, unverified photo, high value, proposed denial; the review queue shows the reason | E1 (tools forced yes/no answers on ambiguity) and Aditya P2 and Trupti P2 (over-escalation floods reviewers) show an **attention-orchestration break** — either the AI decides what it shouldn't, or it floods the human. **Attention & interrogation orchestration** (escalation protocols). |
| M3 | **Evidence strength instead of self-rated confidence** — computed from the checks, with an "Uncertain about" list | E1/F1/F2 (95–100% on wrong answers) and **7 of 7** interviewees asked (100% *lowers* trust; "95%" would be ignored) show a **trust-calibration break**. **Attention & interrogation orchestration** (thresholds the human can interrogate). |
| M4 | **Ambiguity flag** — when the policy hinges on judgment (wear vs. defect), the gate always escalates | E1 (3 of 4 tools denied at 70–100%) and **3 of 3** reviewer-like interviewees asked (trust AI on obvious damage, not on wear vs. defect; *"High confidence shouldn't override obvious ambiguity"* — Aditya P2) show a **reasoning break** on judgment calls. **Role partitioning** (humans own ambiguous calls). |
| M5 | **Photo authenticity check** with an explicit "not verified" state; unverified damage photos are never auto-approved | F1 (0 of 4 detected the fake; Gemini approved its own at 100%) and **3 of 3** reviewer-like interviewees asked, who already check lighting, "too perfect" backgrounds, metadata, and reverse image search, show an **attention break** — AI misses unknown unknowns. **Attention orchestration; knowledge infrastructure** (provenance). |
| M6 | **Rule-based data check before any AI step** — missing evidence routes to "ask the customer", never to a decision | F2 (Claude and Gemini denied for a *missing* photo; Claude's label contradicted its reasoning) and Trupti P1 (*"Tell me what's missing, not just that I'm wrong"*) show a **memory / error-detection break**. **Goals & constraints** (guardrails encoded outside the model). |
| M7 | **Policy clause and version cited on every finding** | F3 (Gemini invented a rule about approvals) and the interviews (*"Showing me the exact policy rule would make the decision feel more legitimate"* — Aditya P1; Sharayu P1; Aditya P2) show a **shared-mental-model break** when provenance is missing. **Knowledge infrastructure** (transparent, auditable provenance). |
| M8 | **Bias safeguards** — customer names and gendered cues removed from model inputs; behavior risk audited for disparate impact | F2 (Claude assumed a customer's gender from their name: *"Her clean history"*) and Sharayu P1 (raised "high-risk" profiling and uneven denials across demographics, unprompted) show a **reasoning / bias-detection break**. **Reasoning** (humans adjudicate fairness; AI inputs minimised). |

### Should have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| S1 | **Override reasons and agreement tracking** — overriding the AI requires a short reason; agreement is broken down by product type and reason | Aditya P2 (*"track when employees override the AI"*), Sharayu P2 (*"how does it learn from human overrides? That feedback loop is crucial"*), and Trupti P2 (wants to see their own override history) show the system cannot improve without a **feedback loop**. **Training & evaluation** (learning from errors, after-action review). |
| S2 | **Customer "request a review"** on a denied return, routed to a reviewer | **4 of 4** customers had a return outcome that felt unexplained or weakly evidenced; Aditya P1 (unprompted) and Sharayu P1 asked for an appeal path — an **accountability break**. **Meta-coordination** (humans manage exceptions). |
| S3 | **Customer-facing explanation** — plain-English reason, the policy rule applied, the evidence considered, and **who decided** (automatically, or a person) | Aditya P1, Sharayu P1, and Trupti P1 want the rule and the evidence; Trupti P1 wants to know *which one* made the decision — a **trust-calibration break** on the customer side. **Knowledge infrastructure** (collaborative artifacts). |
| S4 | **Admin automation switch and thresholds** — automation off by default; an admin turns it on with evidence | Customers are comfortable with AI handling straightforward cases (Aditya P1, Sharayu P1), and reviewers want time back on easy approvals (Aditya P2, Sharayu P2) — automation only within **human-set limits**. **Goals & constraints.** |
| S5 | **"Show me where to look" reviewer view** — the photo area behind the AI's finding is highlighted; disagreeing takes one click with a predefined reason | Aditya P2, Sharayu P2, and Trupti P2 asked for exactly this (*"Show me where to look — I'll tell you if it's right"*), and warned that fast recommendations turn reviewers into "validators" who rubber-stamp — an **interrogation break**. **Attention & interrogation orchestration.** |

### Could have

| ID | Feature | Evidence → break → principle |
|---|---|---|
| C1 | **Full audit log** of every check, gate decision, and human action | Supports S1 and accountability (Aditya P1 blamed the store, not the AI, for relying on it without safeguards). **Knowledge infrastructure** (audit trails). Built underneath M1–S5 rather than as a visible feature. |
| C2 | **Random spot-check sampling** of AI decisions, including auto-approvals | Sharayu P2's team already audits a random sample of decisions monthly; Trupti P2's leads spot-check grades — a guard against silent drift. **Training & evaluation.** |
| C3 | **Physical inspection hand-off** — a disputed damage claim can be confirmed when the item arrives | Trupti P2: the photo check should be *"a pre-check before physical inspection"* — *"A photo shows you an angle, not the shoe."* **Attention** (two gates catch different things). |

### Not now (and why)

Multiple automation levels, fraud-ring visualisation, and an analytics dashboard beyond
agreement, overrides, and escalation rate: no prompting or interview evidence pointed to
them, so they would be features justified only by assumption.

---

## 4. How this changes the design

The Must features and S1–S4 are carried into `DESIGN_SPEC.md` v1 and the prototype. Compared
with v0, the evidence **adds** M2's named escalation reasons, M3's evidence strength, M4's
ambiguity flag, M5's photo authenticity check, M6's pre-AI data check, M8's bias safeguards,
S1's breakdown of overrides, and S2's request-a-review; and **confirms** M1 (human-only
denials) and M7 (policy provenance), which v0 already had.

S5 and M8 came from the later interviews: both are specified in `DESIGN_SPEC.md` v1 and will
be built into the reviewer screen and pipeline in Checkpoint 3 (the clickthrough prototype
does not show them yet). C2–C3 are planned for Checkpoint 3.
