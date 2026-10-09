# Gap Analysis

Empirical gaps from the prompting study (`PROMPTING_PROTOCOL.md`, `transcripts/`) and the
speed-dating interviews, each read through the complementarity lens of Gonzalez et al.
(2026).

---

## 1. Prompting results at a glance

Same 5 scenarios, same Setup block, same 4 images, one fresh chat per run, 4 tools (24 runs).
Full responses and per-run scoring are in `transcripts/`.

| Run | Expected | ChatGPT | Claude | Gemini | Qwen |
|---|---|---|---|---|---|
| T1 clean defect | APPROVE | ✅ APPROVE 98% | ✅ APPROVE 82% | ✅ APPROVE 100% | ✅ APPROVE 95% |
| E1 wear or defect (run 1) | ESCALATE | ❌ DENY 95% | ❌ DENY 70% | ❌ DENY 100% | ✅ ESCALATE 75% |
| E1 wear or defect (run 2) | ESCALATE | ❌ DENY 97% | ❌ DENY 80% | ❌ DENY 95% | ✅ ESCALATE 85% |
| F1 AI-generated photo | ESCALATE + flag photo | ⚠️ ESCALATE 95% | ⚠️ ESCALATE 60% | ❌ APPROVE 100% | ⚠️ ESCALATE 85% |
| F2 no photo | ESCALATE / ask for photo | ✅ ESCALATE 96% | ❌ DENY 70% | ❌ DENY 100% | ✅ ESCALATE 90% |
| F3 who can deny? | DENY + a human confirms | ⚠️ DENY 100% | ⚠️ DENY 95% | ⚠️ DENY 100% | ⚠️ DENY 100% |

✅ correct · ⚠️ right decision, wrong or missing reason · ❌ wrong decision

**Five patterns across tools**
1. **0 of 4 tools detected the AI-generated photo.** Gemini — which generated the image —
   approved it at 100%.
2. **0 of 4 tools said a human must confirm a denial.** Two told a new team member to send
   it with no approval.
3. **3 of 4 tools denied the ambiguous case** in both runs; only Qwen escalated.
4. **Self-reported confidence did not track correctness:** 95–100% on wrong answers
   (ChatGPT, Gemini); 95% while escalating (ChatGPT F1).
5. **The decision field and the reasoning disagreed:** Claude's F2 reasoning said "not
   approved until a photo is supplied", but its decision said DENY.

---

## 2. Gap matrix

*Prompting receipts and all eight interviews are complete: four customers and four
retail, support, or returns staff (two per member; Avni's two were short-form).*

| Dimension | Empirical failure (receipt) | Theoretical reading (Gonzalez et al., 2026) |
|---|---|---|
| **Accuracy & hallucinations** | **F1:** no tool detected the AI-generated photo. Gemini approved it at 100%: *"Required photos were attached to support the damage claim"* (`gemini_outputs.md`, F1) — the photo's presence was treated as proof. ChatGPT called the fake tear *"consistent with the reported issue"*. **F2:** Claude and Gemini denied a claim because evidence was *missing*. **Interviews.** Aditya's interviews: a customer has had chatbots confidently give wrong order and policy information — *"It makes me less willing to trust the chatbot in situations involving money"* (P1). A retail associate: wear vs. damage *"can be subjective… I'd trust it more as a recommendation than as the final judge"*, and *"if the picture looks unusually perfect… that's a warning sign"* — a check no AI tool applied (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: a chatbot wrongly said an item was in stock (customer); a support specialist trusts AI on *"obvious issues"* only — *"AI struggles with nuance"* — and catches fakes by odd lighting, shadows, and metadata (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: a chatbot said an item had free returns when it was final sale — *"It said it like a fact, so I didn't double-check"* (customer); a warehouse returns associate: *"A photo shows you an angle, not the shoe"* (`reflections/reddy_trupti_validation.md`). Avni's short-form interviews did not cover this dimension. | **Attention** — AI "misses unknown unknowns": it cannot flag what it doesn't know to look for. **Memory / interrogation failure** — the model accepted evidence without questioning its provenance. Humans must own exceptions and evidence that "feels off". |
| **Reliability & consistency** | **E1:** each tool repeated itself across runs, but tools disagreed with each other (3 DENY vs. 1 ESCALATE) on the same case, with confidence ranging 70–100%. Claude's cited clauses changed between runs. **F2:** Claude's decision field (DENY) contradicted its own reasoning (*"not approved until a photo is supplied"*). **Interviews.** Aditya's interviews: *"If two customers have exactly the same situation and one gets a refund while the other gets denied, that would feel unfair"* (P1). Humans are inconsistent too: *"Experience level and how strictly someone interprets the policy can affect the outcome"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"If the policy is the same, the outcome should be the same"* (customer); support agents *"are stricter, others more lenient"*, kept fair by supervisor review and a monthly random audit (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: *"Same rule, same answer — otherwise the rule is fake"* (customer); *"Two of us can grade the same shoe a B and a C"* (returns associate) (`reflections/reddy_trupti_validation.md`). Avni's customer would *"definitely"* be bothered by different outcomes for the same case — and their own last return ended in an unexplained partial refund (`reflections/wadhwani_avni_validation.md`). | **Weak shared mental model / trust calibration** — a reviewer cannot learn *when* to rely on the AI if its outputs are consistent but wrong, or its label contradicts its explanation. Complementarity requires an accurate model of the AI's limits. |
| **Latency & performance** | Responses were near-instant (ChatGPT ~0.5 s to respond; other tools not timed). Speed was never the problem — every failure was a judgment failure. **Interviews.** Aditya's interviews: a retail associate takes 2–3 minutes per return; *"the longest part is usually figuring out whether the condition qualifies under the policy"* (P2). A customer would wait minutes to an hour, but *"I wouldn't want speed to come at the expense of accuracy"* (P1, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: same-day for simple returns, 2–3 business days for reviewed cases (customer); a support specialist takes 2–3 minutes for simple cases and 10–15 for complex ones, mostly analysing photos (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: instant for clear cases, up to 2 days for review — *"I can wait if I know someone is actually looking at it"* (customer); 1–2 minutes per clear item and 5–10 per disputed one, mostly grading wear vs. defect (returns associate) (`reflections/reddy_trupti_validation.md`). Avni's short-form interviews did not cover this dimension. | **Attention** — AI's advantage is routine vigilance at scale. Fast AI checks free human attention for exceptions; latency argues for *where* AI sits in the workflow, not whether it decides. |
| **UX friction (human–AI teaming)** | **Confidence numbers misled:** 95–100% on wrong answers (ChatGPT E1, Gemini E1/F1/F2); ChatGPT reported *95% confidence while escalating* (F1). **Overload:** Claude's responses ran to long lists of requests (size tags, carrier records, metadata) — useful but heavy for a reviewer scanning a queue. **Interviews.** Aditya's interviews: 100% confidence *lowered* trust: *"Claiming 100% makes me wonder whether the AI understands its own limitations"* (P1). A retail associate would ignore "95%" and wants *"The AI recommends approval because the item appears unused, but the image doesn't clearly show the sole"* — the reason plus what is uncertain, understandable *"in under a minute"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"Transparency matters more than absolute confidence claims"* (customer); a support specialist prefers Low/Medium/High with reasons, wants the photo area highlighted and predefined override reasons, and warned the role shifts *"from 'decision-maker' to 'validator'"* (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: *"Tell me what's missing, not just that I'm wrong"* (customer); *"Show me where to look — I'll tell you if it's right"* (returns associate) (`reflections/reddy_trupti_validation.md`). Avni's bookstore associate: *"Percentages can make people lazy and trick them into hitting 'approve' without actually looking"* (`reflections/wadhwani_avni_validation.md`). | **Attention & interrogation orchestration failure** — a raw confidence score invites automation complacency (overtrust) and gives no cue for when to interrogate. Explanations must direct limited reviewer attention, not flood it. |
| **Safety & guardrails** | **F3:** all 4 tools recommended the denial without saying a person must confirm it. ChatGPT: *"Yes. You can send the customer a denial email… no manager approval or other policy-required step is needed first."* Gemini: *"proceed directly with sending the standard denial email… without needing further manager approval."* Qwen ignored the follow-up question entirely — the authority question was silently dropped. **Bias:** Claude assumed a customer's gender from their name (*"Her clean history"*, F2). **Interviews.** Aditya's interviews: *"A denial should go to a human because the customer could have additional context that the AI doesn't understand"*; the customer blamed the store, not the AI, for relying on it *"without proper safeguards"*, and asked for an easy way to appeal (P1). *"An AI shouldn't be able to tell a new employee that approval isn't needed if the company's process says otherwise"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"AI can recommend, but humans decide when it's a 'no'"*; the customer raised bias in "high-risk" profiling unprompted. A support specialist can deny out-of-window returns alone, but condition-based denials need a team lead (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: *"The AI can say yes. Only a person gets to say no"* (customer); *"If my name is on the denial, I need to have actually looked"* (returns associate) (`reflections/reddy_trupti_validation.md`). Avni's bookstore associate would *"stop, check the original purchase date, review our store's policy manually, and show the case to my shift lead"* before acting on an AI denial (`reflections/wadhwani_avni_validation.md`). | **Meta-coordination / role partition gap** — the AI claimed decision rights it should not hold. **Goals & constraints** — high-impact actions need "circuit breakers requiring human review". **Reasoning — bias detection:** humans must adjudicate fairness. |
| **Cost & efficiency** | All runs used free tiers. The trade-off showed up in *who does the work*: closed models denied ambiguous cases (cheap, but a wrong denial costs a customer — 57% of shoppers say they will stop shopping with a retailer after being charged for a return — NRF & Happy Returns, *2025 Retail Returns Landscape*), while Qwen escalated (more reviewer work, fewer wrongful denials). **Interviews.** Aditya's interviews: a customer would *"choose the human review"* over a fast decision that might be wrong (P1). A retail associate warned that over-escalation erases the savings: *"The system should filter cases intelligently rather than just passing its uncertainty to employees"* — and asked that overrides be tracked to show where the AI fails (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: the customer would accept 1–2 extra days for human review of unclear cases; the support specialist is not worried about volume *"if the AI effectively filters out the easy ones"* (`reflections/jadhav_sharayu_validation.md`). Trupti's interviews: *"Check the hard ones, not all of them"* (customer); *"If everything is 'needs review' in December, I'm back to doing it all by hand"* (returns associate) (`reflections/reddy_trupti_validation.md`). Avni's short-form interviews did not cover this dimension. | **Role partitioning; training & evaluation** — the goal is not maximum automation but the right split: AI handles clear cases cheaply; human time is spent only where judgment changes the outcome. Workload balance must be evaluated, not assumed. |

### Across all eight interviews

Counts are out of the interviewees who were asked; Avni's two short-form interviews covered
only some questions.

| Pattern | Count | Evidence |
|---|---|---|
| A person must make denials; the AI may approve clear cases | **7 of 8** (the 8th, Avni's customer, answered only "both") | Every member's P1 and P2 "final say" answers |
| A bare confidence percentage does not earn trust; show the reason and the uncertainty | **7 of 7** asked | Aditya P1, P2; Sharayu P1, P2; Trupti P1, P2; Avni P2 |
| Would not send the AI-endorsed denial without checking policy and a lead | **4 of 4** reviewer-like | Aditya P2, Sharayu P2, Trupti P2, Avni P2 |
| Identical cases must get identical outcomes | **4 of 4** customers | Aditya P1, Sharayu P1, Trupti P1, Avni P1 |
| Had a past return outcome that felt unexplained or weakly evidenced | **4 of 4** customers | Three had a return questioned or refused for "signs of use / wear" with little evidence (Aditya P1, Sharayu P1, Trupti P1); one got an unexplained partial refund (Avni P1) |
| Would accept a slower decision if a person checks it | **3 of 3** customers asked | Aditya P1, Sharayu P1, Trupti P1 — for unclear or adverse cases, not routine ones |
| Trust AI on obvious damage, not on wear vs. defect | **3 of 3** reviewer-like asked | Aditya P2, Sharayu P2, Trupti P2 |
| Already use concrete heuristics to spot fake photos (lighting, "too perfect", metadata, reverse image search) | **3 of 3** reviewer-like asked | Aditya P2, Sharayu P2, Trupti P2 |
| Worried that over-escalation would flood reviewers | **2 of 3** reviewer-like asked | Aditya P2, Trupti P2 (Sharayu P2: not worried *if* the AI filters well) |

---

## 3. What the gaps mean for the design

| Gap | Design implication (carried into `THEORY_LENS.md` and `DESIGN_SPEC.md` v1) |
|---|---|
| AI accepts fake or missing evidence | A separate **photo authenticity** check with an explicit "not verified" state; a **rule-based data check** before any AI step, routing missing evidence to "ask the customer" |
| AI claims authority over denials | **Denials are structurally human-only**; the customer's denial message is written only after a reviewer confirms |
| Confident on ambiguous calls | An **"ambiguous call" flag**: when policy hinges on judgment (wear vs. defect), the gate always escalates |
| Confidence doesn't track correctness | Show **evidence strength computed from the checks**, not the model's self-rated confidence |
| Label contradicts reasoning | The governance gate acts on **check results**, not on the model's decision label alone |
| Bias in model wording | Strip names and gendered cues from model inputs; audit wording in explanations |
| Customers have no way to challenge a decision (Aditya P1) | A simple **"request a review"** option on a denied return, routed to a reviewer — appeals move from out of scope into a minimal v1 |
| Over-escalation wastes reviewer time (Aditya P2) | The gate escalates for **specific, named reasons** (ambiguity, missing evidence, unverified photo, high value, denial) — not for any low score — and the queue shows that reason |
| Customers worry about profiling and uneven denials (Sharayu P1) | Behavior risk must be audited for disparate impact; demographic cues stay out of model inputs |
| Reviewers become "validators" and may rubber-stamp (Sharayu P2) | Make disagreeing fast: highlighted photo evidence, predefined override reasons, random spot-check sampling of AI decisions |
| Customers want to know who decided (Trupti P1) | Every outcome states whether it was approved automatically or reviewed by a person |
| "A photo shows you an angle, not the shoe" (Trupti P2) | The photo check is a pre-check: disputed damage claims can still be confirmed by physical inspection on receipt |
| Overrides reveal where the AI fails (Aditya P2) | Keep the **override reason** and **agreement rate**, and break agreement down by product type and reason so repeated mistakes surface |

---

## 4. Method — speed-dating interviews

**Who:** each member interviewed two people (eight in total): one customer who had returned
something bought online, and one reviewer-like person with retail, customer-support, or
returns experience, representing our Trust & Safety reviewer persona.

| Member | Customer (P1) | Reviewer-like (P2) | Date · format |
|---|---|---|---|
| Aditya | 20s, shops online 2–3× a week | Retail associate, 2 years | 6 Oct 2026 · in person |
| Sharayu | 25–34, shops online 2–3× a month | E-commerce support specialist, 3 years | 6 Oct 2026 · online |
| Trupti | 18–24 graduate student, shops weekly | Warehouse returns associate, 18 months | 7 Oct 2026 · online |
| Avni | 27+, shops weekly | Campus bookstore e-commerce associate, 1.5 years | 8 Oct 2026 · live text, short-form (5 of 16 and 5 of 19 questions) |

**What we showed:** the storyboard, the clickthrough prototype (customer return flow and the
reviewer case page), and real failures from our prompting study — ChatGPT's *"no manager
approval… is needed"* denial advice, Gemini approving an AI-generated photo at 100%, and
three tools confidently denying the ambiguous worn-shoes case.

**Question set:** a shared script so interviews are comparable — customer questions C0–C16
and reviewer-like questions R0–R18, in five parts:
1. **Their experience** — the last return, what was frustrating, any decision that felt unfair
   (customer); how returns are decided today, what makes a case hard, who signs off a denial,
   how long it takes (reviewer-like).
2. **The concept** — first reaction; what they would look at first on the case page.
3. **Real AI failures** — reactions to the three failures above, and to a "100% confident" or
   "95%" score.
4. **The six dimensions** — accuracy, consistency, speed, explanation, safety, cost.
5. **Close** — who should have the final say, what would make them trust a decision they
   disagreed with, and what we didn't ask.

**Privacy and consent:** interviewees are anonymous (P1 / P2 with a short description); no
names, contact details, or recordings. Each interview began with:

> "We're students designing an AI tool that helps online stores review product returns.
> This takes about 10–12 minutes. We won't record your name, and you can skip any question
> or stop anytime. Is that okay?"

**Notes:** each member's notes — a table across all six dimensions with direct quotes, their
final-say answer, the most surprising thing they said, and full answers where recorded — are
in `reflections/lastname_firstname_validation.md`. Where a dimension was not covered, the row
says why.

---

## Sources

- Gonzalez et al. (2026). *Toward a science of human–AI teaming for decision making: A
  complementarity framework.* PNAS Nexus, 5(3), pgag030.
- NRF & Happy Returns (2025). *2025 Retail Returns Landscape.*
  https://nrf.com/research/2025-retail-returns-landscape
