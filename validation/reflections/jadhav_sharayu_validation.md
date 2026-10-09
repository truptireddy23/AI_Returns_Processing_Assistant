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
| Who | Customer — age 25–34, shops online 2–3 times a month |
| Date / format | 6 October 2026 · online |
| First reaction to the concept | Helpful if it speeds things up; likes that unclear cases and denials still go to a human ("a safety net"). Main concern: whether the AI can really judge wear and tear from photos without being too strict. |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | A retail chatbot said an item was in stock for pickup; they drove 20 minutes and it wasn't there. Lost trust in the store's automated tools. A fooled image check means the system "is not reliable". | "Confidence shouldn't matter if the input can be faked so easily." |
| Reliability & consistency | Identical cases with different outcomes would feel unfair and arbitrary, and erode trust in the brand. | "If the policy is the same, the outcome should be the same." |
| Latency & performance | Instant or same-day for clear returns; 2–3 business days is fine for a case that needs review; over a week needs a clear explanation. Past frustration: days of "return initiated" with no update. | "Anything longer than a week would start feeling excessive unless they communicated clearly why it was taking longer." |
| UX friction (human–AI teaming) | Wants the policy clause, the evidence the AI used, and — for a denial — a clear path to appeal or request human review. Would trust a moderate score *with a reason* more than "100%". | "Transparency matters more than absolute confidence claims." |
| Safety & guardrails | AI may approve clear cases but should never deny alone: denials affect customers financially and emotionally and need accountability and empathy. Raised bias unprompted: profiling "high-risk" customers from past behaviour, and denials falling unevenly on certain demographics. | "AI can recommend, but humans decide when it's a 'no.'" |
| Cost & efficiency | Would accept 1–2 extra days for human review of disputed or unclear cases; wants simple approvals handled quickly by the AI. | "I value fairness and accuracy over pure speed when the stakes are higher." |

**Who should have the final say (their answer):** Both, with clear roles: the AI handles
clear, low-risk approvals automatically; a person has the final say on any denial or
ambiguous case.

**Most surprising thing they said:**
- **A calibrated number with a reason is fine — certainty is not:** "100% confident" sounds
  *"arrogant and unrealistic"*, but they would trust *"85% confident"* if it explained why
  (e.g. *"the photo clearly shows the item is unworn with tags attached"*). The problem is
  unexplained certainty, not numbers as such.
- **Fraud makes honest customers pay:** if fakes get through, *"honest customers might also get
  caught in stricter policies later because the company tightens rules due to abuse."*
- **Bias and profiling, unprompted:** they asked whether stores flag customers as "high risk"
  from past returns, and whether AI denials fall disproportionately on certain demographics —
  a fairness risk our behavior check must address.
- **Their own past denial was our E1 case:** a jacket zipper that started sticking after two
  wears was denied for "signs of wear", with a generic policy email — *"I ended up letting it go
  because disputing it seemed like too much hassle."*

<details>
<summary>Full interview notes (P1)</summary>

- **C1.** Returned running shoes that were a full size small. Started the return online, printed a label, dropped it off; refund about 10 days after processing.
- **C2.** Had to repackage and find a box; for days the account only said "return initiated", so they wondered whether it had arrived.
- **C3.** A jacket returned after two wears because the zipper stuck was denied for "signs of wear". A generic email cited the "used items" clause and ignored the manufacturing-defect point; they let it go.
- **C4.** Helpful, especially if faster; human review of unclear cases and denials is a safety net. Concern: whether the AI judges wear from photos well, or is too strict.
- **C5.** Would feel frustrated and dismissed; would escalate to customer service or a manager, then perhaps leave a negative review or stop shopping there. "Being denied without any human review feels cold and risky."
- **C6.** Concerning — the system can be fooled; abuse could lead to stricter rules for honest customers; "Confidence shouldn't matter if the input can be faked so easily."
- **C7.** Less trust: "Nothing is 100% certain"; would trust "85% confident" with an explanation more.
- **C8.** A chatbot wrongly said an item was in stock; a wasted 20-minute drive; lost trust in automated tools.
- **C9.** Different outcomes for identical returns would feel unfair and arbitrary.
- **C10.** Instant or same-day for simple returns; 2–3 business days for review; over a week needs communication.
- **C11.** Yes — wants the policy clause, the evidence used (e.g. "item shows signs of wear consistent with use"), and an appeal path for denials.
- **C12.** No AI-only denials; "AI can recommend, but humans decide when it's a 'no.'"
- **C13.** Would accept 1–2 extra days for human review of unclear cases; simple approvals should be fast.
- **C14.** Both, with clear roles: AI for clear low-risk approvals, a person for any denial or ambiguous case.
- **C15.** Seeing the policy rule and evidence, plus an easy appeal to a human who genuinely re-evaluates.
- **C16.** Ask about customer data used to train the AI, "high risk" flagging from past returns, and whether denials fall disproportionately on certain demographics.

</details>

### P2

| Field | Notes |
|---|---|
| Who | Reviewer-like — 3 years as an e-commerce customer support specialist handling returns for a mid-sized online clothing retailer |
| Date / format | 6 October 2026 · online |
| First reaction to the concept | Helpful: photos, history, and policy in one place would stop the tab-switching and speed things up — but they would need to trust the data it presents. |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | Trusts AI on obvious issues (large stains, missing buttons) but not subtle ones — leather texture can look like damage. Today fake photos are caught by intuition (odd lighting, shadows, textures) and metadata; suggests reverse image search and dedicated AI-image detectors. | "AI struggles with nuance." |
| Reliability & consistency | Agents vary — some stricter, some more lenient. Fairness comes from clear guidelines, training, mandatory supervisor review of denials, and a monthly audit of a random sample of decisions. | "Some agents are stricter, others more lenient." |
| Latency & performance | A simple approval takes 2–3 minutes; a complex one 10–15. The slowest part is analysing photos and cross-referencing product details and history. A recommendation in seconds would raise throughput. | "The longest part is usually analyzing the photos and cross-referencing them with the product details and customer history." |
| UX friction (human–AI teaming) | Wants the AI's reasoning side by side with the evidence: highlight the area in the photo, cite the rule, and offer quick override options with predefined reasons. Prefers Low/Medium/High plus contributing factors over "95%". Also wants the product description, care instructions, and customer chat logs. Warned their role would shift from decision-maker to validator. | "It would shift my role from 'decision-maker' to 'validator,' which requires a different kind of focus." |
| Safety & guardrails | Would not send the AI-endorsed denial: checks the clause, the photos, the history, and consults a senior colleague — denials risk chargebacks and bad reviews. Denials on subjective criteria and high-value approvals always need a human; prefers shared responsibility for denials. | "Denying a return is sensitive and can lead to chargebacks or negative reviews." |
| Cost & efficiency | Freed time would go to complex cases, customer communication, and fraud investigation. Not worried about volume if the AI genuinely filters out easy cases. | "In fact, it would make my job more engaging and less repetitive." |

**Who should have the final say (their answer):** Both, with a clear hierarchy: the AI handles
straightforward approvals automatically; for anything ambiguous or involving a denial, a human
must have the final say.

**Most surprising thing they said:**
- **Objective vs. subjective denials are already split at work:** they can deny an
  out-of-window return alone, but a denial based on condition ("item appears worn") needs a
  team lead's approval first — the same line our ambiguity flag draws.
- **From decision-maker to validator:** they named the automation-complacency risk
  themselves — fast AI recommendations change the human's job and *"require a different kind
  of focus"*, so the UI must make it easy to disagree, not just to agree.
- **Random audits already exist:** their team audits a random sample of decisions every month
  — a ready-made model for sampling auto-approved cases for spot checks.
- **Their concrete fix for wear-vs-damage:** route to a human below a threshold and *explain
  why* it is uncertain — *"photo quality is low" or "wear pattern is ambiguous."*

<details>
<summary>Full interview notes (P2)</summary>

- **R1.** Three inputs: the return reason, the item's condition from customer photos, and purchase history. Size exchanges with tags on are near-automatic; "damaged" needs clear photos; frequent or suspicious returners go to a supervisor.
- **R2.** Hard cases are subjective ("not as expected", minor wear vs. defect). Example: a high-end leather jacket "scratch" that looked like natural grain; they compared stock photos and consulted the product team, which took days.
- **R3.** They can deny objective cases (outside the 30-day window) alone; condition-based denials need a team lead's approval before the customer is told.
- **R4.** Simple approvals 2–3 minutes; complex ones 10–15; photo analysis and cross-referencing take longest.
- **R5.** Helpful — everything in one place saves tab-switching — but they would need to trust the data.
- **R6.** Would look first at return history and photos. Missing: the original product description, care instructions, and a link to chat logs with the customer.
- **R7.** Would not send it: would check the clause, review the photos, confirm the history, and consult a senior colleague — denials can cause chargebacks or negative reviews.
- **R8.** Flag as "uncertain / needs human review" instead of denying; route below a threshold (e.g. 90%) and explain the uncertainty ("photo quality is low", "wear pattern is ambiguous").
- **R9.** Today: intuition (odd lighting, inconsistent shadows, unnatural textures) and metadata. Improvements: reverse image search, dedicated generative-artifact detectors.
- **R10.** A raw percentage isn't useful; prefers Low/Medium/High or an explanation, e.g. "High Confidence: Photo clearly shows tear in seam."
- **R11.** Not fully — trusts AI on obvious issues, not subtle ones like leather texture.
- **R12.** Agents vary; guidelines, training, mandatory supervisor review of denials, and a monthly random audit keep it fair.
- **R13.** Would handle more cases per hour, but must avoid blindly accepting recommendations — the role becomes "validator".
- **R14.** Side-by-side reasoning and evidence, the photo area highlighted, the policy rule cited, and quick override options with predefined reasons.
- **R15.** Human oversight on all denials, especially subjective ones, and on high-value approvals; prefers shared responsibility for denials.
- **R16.** Would spend freed time on complex cases, customer communication, and fraud investigation; not worried about volume if the AI filters well.
- **R17.** Both, with a clear hierarchy: AI for straightforward approvals; a human for anything ambiguous or any denial.
- **R18.** Ask about edge cases (e.g. extended holiday return windows), integration with inventory systems, and how the AI learns from human overrides.

</details>

---

## 3. Class-generated storyboard (Step 10)

![ReturnGuard storyboard: a damaged-sneakers return moving through customer submission, data check, policy RAG, image and behavior analysis, AI decision and critic, the human governance gate, and the final decision with an audit log](../../proposal/storyboard.png)

*Class-generated storyboard: a "damaged sneakers" return moving through ReturnGuard. AI can
recommend approval; every denial requires human review.*

---

## 4. One finding that changed (or confirmed) my assumption about the proposed scenario (Step 10)

**Confirmed — with a sharper line: humans should own judgment calls, not just "denials".**

I started with our team's assumption that the key split was simple: the AI approves, a
person denies. My testing and interviews confirmed that humans must own adverse decisions,
but showed the real line is **judgment**. Qwen, the tool I tested, was the only one of the
four that escalated the worn-shoes case in both runs, explaining that *"a definitive APPROVE
or DENY carries a high risk of error given the visual ambiguity"* — yet on the authority
question it recommended a denial at 100% confidence and silently skipped asking whether a
person should confirm it. Every tool handled the objective date check correctly. My support
specialist described the same split from inside a real returns team: they can deny an
out-of-window return alone, but a denial based on condition ("item appears worn") needs a
team lead's approval first. My customer put it simply: *"AI can recommend, but humans
decide when it's a 'no.'"*

Through Gonzalez et al. (2026), this is **role partitioning** grounded in the **reasoning**
pillar. Complementarity works when human and AI error patterns differ: the AI was reliable
on rule-based facts like return windows but unreliable on subjective condition calls and on
knowing its own authority — exactly where humans add judgment, context, and accountability.
It confirmed our "AI never denies" rule and explains why v1 adds an ambiguity flag that
always escalates judgment calls. My specialist's warning that fast recommendations turn
reviewers into "validators" also showed me that partitioning roles is not enough on its own:
the interface has to make disagreeing with the AI as easy as agreeing, or the human check
becomes a rubber stamp.
