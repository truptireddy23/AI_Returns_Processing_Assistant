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
| Who | Customer — in their 20s, shops online 2–3 times a week, has returned several items (mostly clothing and shoes) |
| Date / format | 6 October 2026 · in person |
| First reaction to the concept | Useful if it makes returns faster. Comfortable with AI handling straightforward cases, but wants a human involved whenever there is disagreement or uncertainty. |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | Chatbots have confidently given them wrong order and return-policy information; they had to check the company website themselves. This lowers trust whenever money is involved. A fake photo approved at 100% showed them the confidence score "isn't reliable by itself". | "It makes me less willing to trust the chatbot in situations involving money." |
| Reliability & consistency | Consistency matters most when money is at stake; identical cases with different outcomes would feel unfair. | "If two customers have exactly the same situation and one gets a refund while the other gets denied, that would feel unfair." |
| Latency & performance | Happy to wait minutes or up to an hour for a simple return; a multi-day wait needs a stated reason. Their real frustration last time was not knowing when the refund would arrive. | "Speed is nice, but I wouldn't want speed to come at the expense of accuracy." |
| UX friction (human–AI teaming) | Wants to see the exact policy rule plus what the AI considered (return date, reason, photos, signs of damage or use). Prefers a confidence *band* with evidence over a percentage. | "I'd rather see something like 'high confidence' along with the evidence it used." |
| Safety & guardrails | AI may approve simple cases but should never deny alone; wants safeguards against manipulated photos. Holds the store — not the AI — responsible for unsafe automation. | "A denial should go to a human because the customer could have additional context that the AI doesn't understand." |
| Cost & efficiency | Would trade speed for human verification, especially on expensive purchases. | "If the choice is between getting an immediate decision that might be wrong and waiting another day for a human to verify it, I'd choose the human review." |

**Who should have the final say (their answer):** Both should be involved, but the person
has the final say. AI handles routine cases and gives the reviewer evidence and a
recommendation; the human can override the AI.

**Most surprising thing they said:**
- **"100% confident" made them trust the AI *less*, not more:** *"Claiming 100% makes me
  wonder whether the AI understands its own limitations."* High stated confidence acted as a
  red flag — the opposite of what the tools seem to assume.
- **They blamed the store, not the AI,** for the unsafe denial advice: *"I wouldn't blame the
  AI as much as the store for relying on it without proper safeguards."* Accountability
  sits with whoever deploys the AI.
- **They raised appeals unprompted** (C15, C16): customers need an easy way to challenge a
  decision. Appeals are out of scope in our v0 design — a gap the interview exposed.
- **Their past bad experience was exactly our E1 case:** a return was questioned for "signs
  of use" after only trying the item on, with *"not much evidence"* and no way to challenge
  it — the same wear-vs-defect ambiguity three AI tools denied.

<details>
<summary>Full interview notes (P1)</summary>

- **C1.** Last return: shoes that didn't fit. Submitted on the website, printed a label, shipped them back; refund came after the store received them.
- **C2.** Frustrating part: not knowing when the refund would arrive (tracking showed delivered, refund took days); had to read the return policy to check nothing was missed.
- **C3.** Had a return questioned for "signs of use" after only trying it on. The store gave little evidence: "That felt unfair because I didn't really have a way to challenge their assessment."
- **C4.** Useful, especially if faster; AI for straightforward cases, human for disagreement or uncertainty.
- **C5.** Would be frustrated; blames the store more than the AI for relying on it without safeguards; would ask for a manager review and an explanation.
- **C6.** Concerned — the confidence score isn't reliable by itself; wants safeguards against manipulated photos rather than automatically trusting images.
- **C7.** 100% confidence lowers trust: "Real-world situations aren't usually that certain." Prefers "high confidence" plus the evidence used.
- **C8.** Chatbots have given wrong order/policy info; had to verify on the website; less willing to trust chatbots where money is involved.
- **C9.** Inconsistent outcomes for identical cases would feel unfair, especially with money involved.
- **C10.** Minutes to an hour is fine for simple returns; days need a reason; speed shouldn't cost accuracy.
- **C11.** Showing the exact policy rule makes a decision feel more legitimate; also wants to see the date, reason, photos, and damage/use assessment the AI considered.
- **C12.** AI shouldn't deny on its own; approvals of simple cases are fine; customers may have context the AI lacks.
- **C13.** Would wait a day for human review rather than get a fast decision that might be wrong — especially for expensive items.
- **C14.** Both, with the person having the final say and able to override.
- **C15.** Needs a clear explanation, the policy applied, and a way to appeal; knowing a real person looked at the case matters.
- **C16.** Consider what happens when the AI is wrong: easy appeals, and stores shouldn't blindly trust a confidence score. Comfortable with AI assisting, not with AI fully controlling adverse decisions.

</details>

### P2

| Field | Notes |
|---|---|
| Who | Reviewer-like — 2 years as a retail associate, regularly handled customer returns and exchanges |
| Date / format | 6 October 2026 · in person |
| First reaction to the concept | Could be really useful: having the order, policy, photos, and AI recommendation in one place would save time. But they would not want the AI to make the final decision by itself. |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | AI may handle obvious damage, but wear vs. customer-caused damage is subjective; lighting, photo quality, and product type all matter. Trusts AI as a recommendation, not a judge. Today they catch suspicious photos by looking for inconsistencies, asking for more photos, or inspecting the item. | "I'd trust it more as a recommendation than as the final judge." |
| Reliability & consistency | Different staff do decide borderline returns differently — experience and how strictly someone reads the policy change the outcome. Clear guidelines, examples of acceptable conditions, and supervisor review keep it consistent. | "Experience level and how strictly someone interprets the policy can affect the outcome." |
| Latency & performance | A normal return takes 2–3 minutes; the slow part is judging whether the condition qualifies, especially when they must look something up or ask a manager. Would use an AI recommendation that arrives in seconds, especially for straightforward cases. | "The longest part is usually figuring out whether the condition qualifies under the policy." |
| UX friction (human–AI teaming) | Wants the recommendation, the policy rule, order details, photo evidence, and what the AI is unsure about — all on one screen, understandable in under a minute. Would ignore a bare "95%" without knowing what it means. | "I'd rather see something like: 'The AI recommends approval because the item appears unused, but the image doesn't clearly show the sole.'" |
| Safety & guardrails | A person must check disputed damage, expensive items, suspected fraud, unclear photos, and denials that could cause a significant customer issue. Comfortable signing off if given enough evidence. The AI should flag suspicious images rather than assume every photo is genuine. | "An AI shouldn't be able to tell a new employee that approval isn't needed if the company's process says otherwise." |
| Cost & efficiency | Offloading straightforward approvals would free time for complicated customers. But if the AI sends every slightly unusual case to a person, it saves nothing. | "The system should filter cases intelligently rather than just passing its uncertainty to employees." |

**Who should have the final say (their answer):** Both, but the person has the final say. The
AI does the initial review and recommends; the employee handles exceptions and questionable
cases. The AI should never have authority to deny someone without human oversight.

**Most surprising thing they said:**
- **Too much escalation is its own failure:** *"The system should filter cases intelligently
  rather than just passing its uncertainty to employees."* Escalating everything that is
  slightly unusual would erase the time savings — the gate must be selective, not just
  cautious.
- **Overrides are data:** unprompted, they asked the company to *"track when employees
  override the AI, because those overrides could reveal where the AI isn't working well"*,
  and wanted a way to report repeated mistakes on a product type. This independently
  confirms our override-reason and agreement-rate design.
- **They described our "Why not higher" design in their own words:** a recommendation plus
  the reason plus what the image doesn't show — instead of a percentage they would ignore.
- **Their hardest real case is our E1 scenario:** shoes that looked worn, from a customer who
  said they wore them once — *"It wasn't obvious from looking at them whether that counted as
  normal use or a defect."*
- **A too-perfect photo is a warning sign:** *"If the picture looks unusually perfect or
  doesn't match the customer's description, that's a warning sign"* — a human heuristic
  none of the AI tools applied in F1.

<details>
<summary>Full interview notes (P2)</summary>

- **R1.** Check the receipt or order, the purchase date and return window, then the item's condition against the policy. Damage, heavy use, or anything unusual goes to a supervisor before approval.
- **R2.** Hard cases: unclear whether the customer caused the damage or it was defective — e.g. shoes that looked worn from a customer who said they wore them once because they were uncomfortable.
- **R3.** The associate approves normal cases; a supervisor or manager decides unusual or questionable denials, especially ones that could lead to a complaint.
- **R4.** A normal return takes 2–3 minutes; the slowest part is judging whether the condition qualifies, looking things up, or asking a manager.
- **R5.** Useful to have the order, policy, photos, and AI recommendation in one place; would not want the AI to make the final decision alone.
- **R6.** Would look first at the return reason, then the photos. Wants the purchase date, return deadline, order info, the exact policy rule, and *why* the AI reached its conclusion — not just "approve" or "deny".
- **R7.** Would not send the denial immediately: would check the policy, confirm the case qualifies, and check whether manager approval is required.
- **R8.** The AI should recognise uncertainty instead of forcing yes/no — say "Needs human review" and explain what is uncertain. "High confidence shouldn't override obvious ambiguity."
- **R9.** Today: look for inconsistencies, ask for more photos, or inspect the item. A photo that looks unusually perfect or doesn't match the description is a warning sign; wants the system to flag suspicious images.
- **R10.** Would ignore "95%" unless they knew what it meant; prefers the recommendation with its reason and what the evidence doesn't show.
- **R11.** Not completely — wear vs. damage is subjective; lighting, photo quality, and product type matter. A recommendation, not the final judge.
- **R12.** Staff decide borderline cases differently based on experience and strictness; guidelines, examples, and supervisor review help.
- **R13.** Would use a recommendation that arrives in seconds, especially for straightforward cases.
- **R14.** Recommendation, policy rule, order details, photo evidence, and uncertainties on one screen — understandable in under a minute.
- **R15.** No final AI decisions on disputed damage, expensive items, suspected fraud, unclear photos, or high-impact denials. Comfortable signing off with enough evidence.
- **R16.** Would gain time for complex customers; worried the AI would send every slightly unusual case to them.
- **R17.** Both, with the person having the final say; the AI should not deny without human oversight.
- **R18.** Wants to know how the AI learns and is monitored; a way to report repeated mistakes; and tracking of employee overrides to reveal where the AI fails.

</details>

---

## 3. Class-generated storyboard (Step 10)

![ReturnGuard storyboard: a damaged-sneakers return moving through customer submission, data check, policy RAG, image and behavior analysis, AI decision and critic, the human governance gate, and the final decision with an audit log](../../proposal/storyboard.png)

*Class-generated storyboard: a "damaged sneakers" return moving through ReturnGuard. AI can
recommend approval; every denial requires human review.*

**My v1 storyboard (after Checkpoint 2).** The same damaged-sneakers return, retold through
the refined design. Panels marked *NEW in v1* come from the prompting and interview evidence:
the rule-based data check, separate photo authenticity check, evidence strength instead of a
confidence percentage, a gate that escalates only for named reasons, and a customer's
request a review.

![ReturnGuard v1 storyboard: Maya submits a damaged-sneakers return; a rule-based data check, policy check, photo match/authenticity/condition checks, and history check run; the AI recommends with evidence strength; the governance gate auto-approves only when all checks are clear or routes to a reviewer for a named reason; Riley decides with a confirm step for denials; Maya sees the rule, the evidence, and a request-a-review option](kamath_aditya_storyboard_v1.png)

---

## 4. One finding that changed (or confirmed) my assumption about the proposed scenario (Step 10)

**Changed: showing the AI's confidence score does not build trust — it can break it.**

Going into this checkpoint, I assumed that showing a confidence score next to each AI
recommendation would help reviewers and customers trust the system, so our v0 design put a
percentage on the case page. My ChatGPT runs showed the score had no link to correctness: it
denied the ambiguous worn-shoes case at 95% and then 97%, reported 95% confidence *while
escalating* the fake-photo case, and answered the authority question at 100% — then flipped
to "APPROVE, 95%" on a re-run. The interviews pointed the same way from the human side. My
customer said high confidence lowered their trust: *"Claiming 100% makes me wonder whether
the AI understands its own limitations."* My retail associate said they would *"probably
ignore a score like '95%'"* and wanted the reason and what the AI was unsure about instead.

Through the lens of Gonzalez et al. (2026), this is a **trust calibration** problem.
Complementarity depends on the human having an accurate model of what the AI can and cannot
do, so they rely on it neither too much nor too little. A self-reported score that stays
near 100% whether the AI is right or wrong pushes people toward one of the two failure
modes the paper describes: automation complacency (trusting the number) or algorithm
aversion (ignoring it, as my associate would). That changed our design: v1 replaces the
percentage with evidence strength computed from the checks, plus an "Uncertain about" list,
so the reviewer calibrates trust on the evidence rather than on the model's opinion of
itself.
