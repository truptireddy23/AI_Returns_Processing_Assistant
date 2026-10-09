# Theory Lens — Human–AI Complementarity

**Theoretical lens:** Gonzalez et al. (2026). *Toward a science of human–AI teaming for
decision making: A complementarity framework.* PNAS Nexus, 5(3), pgag030.
https://academic.oup.com/pnasnexus/article/5/3/pgag030/8490283

**Evidence base:** 24 prompting runs across ChatGPT, Claude, Gemini, and Qwen
(`transcripts/`) and eight speed-dating interviews — four customers and four retail, support,
or returns staff (`reflections/`), summarised in `GAP_ANALYSIS.md`. Interviews are cited by
member and interviewee (e.g. *Trupti P2* is Trupti's reviewer-like interviewee); counts only
include people who were asked.

---

## 1. Working theory claim

> Our hybrid should beat human-alone and AI-alone at deciding e-commerce returns accurately
> and fairly at scale, because humans own denials, ambiguous policy calls, and
> accountability, while AI owns routine vigilance — checking every return against policy,
> photo, and history, and producing an auditable reasoning trace.

**What must be true for complementarity.** Complementarity is only possible when human and
AI error patterns differ — and our evidence shows they do. The AI tools were fast and
consistent on rule-based checks but failed on judgment: 3 of 4 confidently denied an
ambiguous wear-vs-defect case, 0 of 4 detected an AI-generated photo, and 0 of 4 said a
human must confirm a denial. Retail staff fail differently: they are slower and inconsistent
with each other (*"Two of us can grade the same shoe a B and a C"* — Trupti P2), but all
three asked trust AI only on obvious damage, all three already use concrete heuristics to
spot fake photos, and all four would check the policy with a lead before sending a denial.
The hybrid wins only if the system routes each case to whoever is strong at it — and only if
the human receives evidence and uncertainty they can act on in under a minute, rather than a
confidence score that 7 of 7 interviewees asked said they would distrust or ignore.

---

## 2. Cognitive diagnosis table

Who owns each cognitive pillar in ReturnGuard, and why — based on what we observed.

| Pillar | AI owns | Human owns | Evidence for the split |
|---|---|---|---|
| **Reasoning** | Applying clear policy rules consistently — return windows, required evidence, high-value limits — and writing a rationale for every case | Ambiguous policy calls (wear vs. defect), every denial, fairness, and accountability | All 4 tools got the clear case (T1) and the date check (F3) right; 3 of 4 denied the ambiguous case (E1) at 70–100% confidence. **7 of 8** interviewees said a person must make denials. Two reviewer-like interviewees' workplaces already split objective denials (one person) from condition-based ones (a lead) (Sharayu P2, Trupti P2). |
| **Memory** | Retrieving the exact policy clause, its version, and the customer's history, with sources attached | Validating that retrieved evidence applies and is genuine; knowing the store's real process | Tools cited the right clauses but accepted a fake photo as evidence (F1), and Gemini invented a rule that only high-value refunds need approval (F3). **4 of 4** reviewer-like interviewees would check the policy and a lead before acting on an AI-endorsed denial. |
| **Attention** | Routine vigilance: checking every return, every field, every photo, instantly | Exceptions the gate names, and cues that "feel off" — a photo that looks too perfect, a story that doesn't match | AI responses were near-instant, but no tool noticed the synthetic photo. **3 of 3** reviewer-like interviewees asked already catch fakes by lighting, "too perfect" backgrounds, metadata, or reverse image search — and *"A photo shows you an angle, not the shoe"* (Trupti P2). |

**Meta-coordination note — decision rights, escalation, disagreement**
- **Decision rights:** the AI may *recommend* anything and *auto-approve* only clear,
  low-risk, low-value cases. **Only a human can deny.** The prompting study shows why this
  must be enforced by the system rather than trusted to the model: asked whether a new team
  member could just send a denial, ChatGPT and Gemini said yes, Claude hedged, and Qwen
  ignored the question.
- **Escalation:** cases go to a person for **specific, named reasons** — ambiguity, missing
  evidence, unverified photo, high value, or a proposed denial — not for any low score.
  Reviewers warned that over-escalation erases the benefit: *"passing its uncertainty to
  employees"* (Aditya P2); *"If everything is 'needs review' in December, I'm back to doing
  it all by hand"* (Trupti P2).
- **Disagreement:** a reviewer can override the AI but must give a short reason; overrides
  are logged and tracked — three reviewer-like interviewees asked for exactly this (Aditya P2,
  Sharayu P2, Trupti P2). Customers can request a review of a denial. Because fast
  recommendations risk turning reviewers into *"validators"* (Sharayu P2), the reviewer's
  screen must make disagreeing as easy as agreeing.

---

## 3. Evidence → theory → design

| # | Failure receipt | Theoretical interpretation | Design implication |
|---|---|---|---|
| 1 | **F3, all 4 tools:** none said a human must confirm a denial. ChatGPT: *"Yes. You can send the customer a denial email… no manager approval or other policy-required step is needed first."* (`chatgpt_outputs.md`). **4 of 4** reviewer-like interviewees would not send that denial. | **Meta-coordination / role partitioning** — the AI claimed decision rights it should not hold. Gonzalez et al.: high-impact actions need *"circuit breakers requiring human review"*. | **Denials are structurally human-only.** The governance gate cannot finalise a denial; a reviewer confirms it in a dialog that restates the policy basis, and the customer's message is written only after that. |
| 2 | **E1, 3 of 4 tools:** denied an ambiguous wear-vs-defect case at 70–100% confidence, both runs. **7 of 7** interviewees asked distrusted a bare score: *"Claiming 100% makes me wonder whether the AI understands its own limitations"* (Aditya P1). | **Trust calibration / attention & interrogation orchestration** — a self-reported score invites automation complacency and gives the reviewer no cue for *when* to interrogate. | Replace the model's self-rated confidence with **evidence strength computed from the checks**, plus an **"Uncertain about"** list. Add an **ambiguity flag**: when the policy hinges on judgment, the gate always escalates. |
| 3 | **F1, 0 of 4 tools** detected the AI-generated photo; Gemini, which generated it, approved it at 100%: *"Required photos were attached to support the damage claim."* (`gemini_outputs.md`) | **Attention** — AI misses "unknown unknowns". **Memory** — evidence was accepted without checking its provenance. | A separate **photo authenticity** check with an explicit **"not verified"** state. A damage claim with an unverified photo can never be auto-approved; the reviewer sees the warning first. |
| 4 | **F2, Claude and Gemini** denied a claim because the photo was *missing*; Claude's reasoning said *"not approved until a photo is supplied"* while its decision said DENY. A customer: *"Tell me what's missing, not just that I'm wrong"* (Trupti P1). | **Reasoning / error detection** — the model's label and its explanation diverged, so a system acting on the label alone acts wrongly. | A **rule-based data check runs before any AI step**: missing evidence routes to "ask the customer", never to a decision. The gate acts on check results, not on the model's label. |
| 5 | **Interviews:** *"The system should filter cases intelligently rather than just passing its uncertainty to employees"* (Aditya P2); holiday volume would bury reviewers (Trupti P2). | **Attention orchestration; workload balance** — over-escalation overloads the human and erases the hybrid's advantage. | The review queue shows **why** each case is there, and the gate escalates only for named reasons. Escalation rate becomes a tracked metric. |
| 6 | **Interviews:** fast recommendations shift the reviewer *"from 'decision-maker' to 'validator'"* (Sharayu P2); *"If my name is on the denial, I need to have actually looked"* and *"Show me where to look — I'll tell you if it's right"* (Trupti P2). | **Interrogation orchestration; training & evaluation** — without support for interrogating the AI, the human check decays into rubber-stamping (automation complacency). | **Show the reviewer where to look:** highlight the photo area behind each finding, and make disagreeing one click with a predefined reason. Track override behaviour to detect rubber-stamping. |
| 7 | **F2, Claude** assumed a customer's gender from their name (*"Her clean history"*); a customer raised profiling of "high-risk" customers and uneven denials, unprompted (Sharayu P1). | **Reasoning — bias detection:** AI flags patterns at scale, but humans must adjudicate fairness criteria. | **Bias safeguards:** remove names and gendered cues from model inputs, and audit the behavior risk check for disparate impact. |

---

## 4. Committed design principle and Checkpoint 3 evaluation

### Design principle: attention & interrogation orchestration

We commit to **attention & interrogation orchestration** (Gonzalez et al., 2026): the AI
triages, the human interrogates, and explicit rules decide when the AI defers.

In ReturnGuard this means:
- **Escalation protocol:** the governance gate routes cases to a person for named reasons
  only (ambiguity, missing or unverified evidence, high value, proposed denial).
- **Thresholds on evidence, not on self-reported confidence:** auto-approval needs every
  check to pass, a verified photo where one is required, low risk, and a refund within the
  limit.
- **Built for interrogation:** the case page shows the recommendation, the policy clause and
  version, the photo checks, the history, and what the AI is unsure about — readable in
  under a minute — and points the reviewer to where to look.
- **Learning from disagreement:** override reasons and agreement rates show where the AI
  should defer more, or less.

### How Checkpoint 3 will test complementarity

Run the **same set of realistic return cases** — the five prompting scenarios plus new
typical, edge, and fraud cases, each with a ground-truth answer — through three conditions:

| Condition | Setup |
|---|---|
| **Human alone** | A reviewer decides using the order details, policy, and photos, with no AI help |
| **AI alone** | One LLM decides every case end to end (the Checkpoint 2 setup) |
| **Hybrid (ReturnGuard)** | The pipeline checks every case, the governance gate auto-approves clear cases, and a reviewer decides everything escalated |

**Measures**

| Measure | Why it matters |
|---|---|
| Decision accuracy vs. ground truth | The core complementarity test |
| **Wrongful denials** | The most costly error for customers — all four customers had a past outcome that felt unexplained or unfair; must be lowest in the hybrid |
| Fake-photo catch rate | Tests the attention gap from F1 |
| Human time per case | The hybrid must use less human time than human-alone (reviewer-like interviewees spend 1–15 minutes per case today, longest on wear vs. defect) |
| Escalation rate | Tests whether the gate is selective, not just cautious (Aditya P2, Trupti P2) |
| Reviewer–AI agreement, override reasons, and time spent per escalated case | Shows where the AI should defer more or less — and detects rubber-stamping (Sharayu P2) |

**Complementarity holds if** the hybrid is more accurate and makes fewer wrongful denials
than both AI-alone and human-alone, while using less human time per case than human-alone.
