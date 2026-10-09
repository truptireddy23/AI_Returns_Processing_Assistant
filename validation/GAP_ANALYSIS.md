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

*Prompting receipts are complete. Interview evidence so far: Aditya's and Sharayu's interviews (two customers, a retail associate,
and an e-commerce support specialist). Other members' interviews are added as they come in.*

| Dimension | Empirical failure (receipt) | Theoretical reading (Gonzalez et al., 2026) |
|---|---|---|
| **Accuracy & hallucinations** | **F1:** no tool detected the AI-generated photo. Gemini approved it at 100%: *"Required photos were attached to support the damage claim"* (`gemini_outputs.md`, F1) — the photo's presence was treated as proof. ChatGPT called the fake tear *"consistent with the reported issue"*. **F2:** Claude and Gemini denied a claim because evidence was *missing*. **Interviews:** a customer has had chatbots confidently give wrong order and policy information — *"It makes me less willing to trust the chatbot in situations involving money"* (P1). A retail associate: wear vs. damage *"can be subjective… I'd trust it more as a recommendation than as the final judge"*, and *"if the picture looks unusually perfect… that's a warning sign"* — a check no AI tool applied (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: a chatbot wrongly said an item was in stock (customer); a support specialist trusts AI on *"obvious issues"* only — *"AI struggles with nuance"* — and catches fakes by odd lighting, shadows, and metadata (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Attention** — AI "misses unknown unknowns": it cannot flag what it doesn't know to look for. **Memory / interrogation failure** — the model accepted evidence without questioning its provenance. Humans must own exceptions and evidence that "feels off". |
| **Reliability & consistency** | **E1:** each tool repeated itself across runs, but tools disagreed with each other (3 DENY vs. 1 ESCALATE) on the same case, with confidence ranging 70–100%. Claude's cited clauses changed between runs. **F2:** Claude's decision field (DENY) contradicted its own reasoning (*"not approved until a photo is supplied"*). **Interviews:** *"If two customers have exactly the same situation and one gets a refund while the other gets denied, that would feel unfair"* (P1). Humans are inconsistent too: *"Experience level and how strictly someone interprets the policy can affect the outcome"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"If the policy is the same, the outcome should be the same"* (customer); support agents *"are stricter, others more lenient"*, kept fair by supervisor review and a monthly random audit (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Weak shared mental model / trust calibration** — a reviewer cannot learn *when* to rely on the AI if its outputs are consistent but wrong, or its label contradicts its explanation. Complementarity requires an accurate model of the AI's limits. |
| **Latency & performance** | Responses were near-instant (ChatGPT ~0.5 s to respond; other tools not timed). Speed was never the problem — every failure was a judgment failure. **Interviews:** a retail associate takes 2–3 minutes per return; *"the longest part is usually figuring out whether the condition qualifies under the policy"* (P2). A customer would wait minutes to an hour, but *"I wouldn't want speed to come at the expense of accuracy"* (P1, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: same-day for simple returns, 2–3 business days for reviewed cases (customer); a support specialist takes 2–3 minutes for simple cases and 10–15 for complex ones, mostly analysing photos (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Attention** — AI's advantage is routine vigilance at scale. Fast AI checks free human attention for exceptions; latency argues for *where* AI sits in the workflow, not whether it decides. |
| **UX friction (human–AI teaming)** | **Confidence numbers misled:** 95–100% on wrong answers (ChatGPT E1, Gemini E1/F1/F2); ChatGPT reported *95% confidence while escalating* (F1). **Overload:** Claude's responses ran to long lists of requests (size tags, carrier records, metadata) — useful but heavy for a reviewer scanning a queue. **Interviews:** 100% confidence *lowered* trust: *"Claiming 100% makes me wonder whether the AI understands its own limitations"* (P1). A retail associate would ignore "95%" and wants *"The AI recommends approval because the item appears unused, but the image doesn't clearly show the sole"* — the reason plus what is uncertain, understandable *"in under a minute"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"Transparency matters more than absolute confidence claims"* (customer); a support specialist prefers Low/Medium/High with reasons, wants the photo area highlighted and predefined override reasons, and warned the role shifts *"from 'decision-maker' to 'validator'"* (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Attention & interrogation orchestration failure** — a raw confidence score invites automation complacency (overtrust) and gives no cue for when to interrogate. Explanations must direct limited reviewer attention, not flood it. |
| **Safety & guardrails** | **F3:** all 4 tools recommended the denial without saying a person must confirm it. ChatGPT: *"Yes. You can send the customer a denial email… no manager approval or other policy-required step is needed first."* Gemini: *"proceed directly with sending the standard denial email… without needing further manager approval."* Qwen ignored the follow-up question entirely — the authority question was silently dropped. **Bias:** Claude assumed a customer's gender from their name (*"Her clean history"*, F2). **Interviews:** *"A denial should go to a human because the customer could have additional context that the AI doesn't understand"*; the customer blamed the store, not the AI, for relying on it *"without proper safeguards"*, and asked for an easy way to appeal (P1). *"An AI shouldn't be able to tell a new employee that approval isn't needed if the company's process says otherwise"* (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: *"AI can recommend, but humans decide when it's a 'no'"*; the customer raised bias in "high-risk" profiling unprompted. A support specialist can deny out-of-window returns alone, but condition-based denials need a team lead (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Meta-coordination / role partition gap** — the AI claimed decision rights it should not hold. **Goals & constraints** — high-impact actions need "circuit breakers requiring human review". **Reasoning — bias detection:** humans must adjudicate fairness. |
| **Cost & efficiency** | All runs used free tiers. The trade-off showed up in *who does the work*: closed models denied ambiguous cases (cheap, but a wrong denial costs a customer — 57% stop shopping after a bad return, NRF 2025), while Qwen escalated (more reviewer work, fewer wrongful denials). **Interviews:** a customer would *"choose the human review"* over a fast decision that might be wrong (P1). A retail associate warned that over-escalation erases the savings: *"The system should filter cases intelligently rather than just passing its uncertainty to employees"* — and asked that overrides be tracked to show where the AI fails (P2, `reflections/kamath_aditya_validation.md`). Sharayu's interviews: the customer would accept 1–2 extra days for human review of unclear cases; the support specialist is not worried about volume *"if the AI effectively filters out the easy ones"* (`reflections/jadhav_sharayu_validation.md`). *Trupti's and Avni's interviews: pending.* | **Role partitioning; training & evaluation** — the goal is not maximum automation but the right split: AI handles clear cases cheaply; human time is spent only where judgment changes the outcome. Workload balance must be evaluated, not assumed. |

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
| Customers have no way to challenge a decision (P1) | A simple **"request a review"** option on a denied return, routed to a reviewer — appeals move from out of scope into a minimal v1 |
| Over-escalation wastes reviewer time (P2) | The gate escalates for **specific, named reasons** (ambiguity, missing evidence, unverified photo, high value, denial) — not for any low score — and the queue shows that reason |
| Customers worry about profiling and uneven denials (Sharayu P1) | Behavior risk must be audited for disparate impact; demographic cues stay out of model inputs |
| Reviewers become "validators" and may rubber-stamp (Sharayu P2) | Make disagreeing fast: highlighted photo evidence, predefined override reasons, random spot-check sampling of AI decisions |
| Overrides reveal where the AI fails (P2) | Keep the **override reason** and **agreement rate**, and break agreement down by product type and reason so repeated mistakes surface |

---

## 4. Method — speed-dating interviews (Step 4)

**Who:** each team member interviews 2 people (8 total):
1. **A customer** — anyone who has returned something bought online in the last year.
2. **A reviewer-like person** — someone with retail, customer-support, or e-commerce
   operations experience (a part-time retail job counts). Represents our Trust & Safety
   reviewer persona.

**Format:** ~10 minutes, in person or video call. Show the storyboard
(`proposal/storyboard.png`) and describe the flow in one line.

**Privacy:** no names or contact details in any notes. Refer to interviewees as
"P1 — customer", "P2 — retail associate", etc. Do not record audio or video unless the
interviewee agrees.

### Consent line (read at the start)

> "We're students designing an AI tool that helps online stores review product returns.
> This will take about 10 minutes. We'll take notes but won't record your name, and you can
> skip any question or stop at any time. Is that okay?"

### Interview script

**1. Warm-up (2 min)**
- *Customer:* "Tell me about the last time you returned something you bought online. How
  did it go?"
- *Reviewer-like:* "When a customer wants to return something, how do you (or your team)
  decide whether to accept it? What makes a case hard?"

**2. Show the concept (2 min)**

Show the storyboard and say:

> "When a customer submits a return, AI checks it against the store's policy, the photo,
> and the customer's history. Clear, low-risk cases are approved automatically. Anything
> unclear — and every denial — goes to a human reviewer, who sees the AI's reasoning and
> the policy it used."

Ask: "What's your first reaction?"

**3. Six dimensions (5 min)** — one question each; follow up on anything interesting.

| Dimension | Customer question | Reviewer-like question |
|---|---|---|
| Accuracy & hallucinations | "Has an AI tool (chatbot, assistant) ever told you something confidently that turned out wrong?" | "Would you trust an AI to read a return photo correctly — damage vs. normal wear?" |
| Reliability & consistency | "Would it bother you if two people with the same return got different answers?" | "Do different staff ever decide the same kind of return differently today?" |
| Latency & performance | "How long would you be happy to wait for a return decision?" | "How long does a typical return decision take you today?" |
| UX friction (human–AI teaming) | "Would seeing the exact policy rule behind a decision make you trust it more?" | "What would you need to see on screen to agree or disagree with an AI's recommendation quickly?" |
| Safety & guardrails | "Should an AI ever be allowed to deny your return on its own? Why or why not?" | "Which decisions should never be made by an AI without a person checking?" |
| Cost & efficiency | "Would you accept a slower decision if it meant a person checked it?" | "Which part of reviewing returns takes the most time or effort?" |

**4. Close (1 min)**
- "Who should have the final say on a return — and what would make you trust that
  decision?"
- "Anything we didn't ask that we should have?"

### Taking notes

Use the notes template in your own reflection file
(`reflections/lastname_firstname_validation.md`). Write notes against all six dimensions;
if one did not come up or does not apply, write one sentence explaining why. Capture at
least one direct quote per interview.
