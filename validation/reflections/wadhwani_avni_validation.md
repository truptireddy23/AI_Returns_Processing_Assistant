# Validation Reflection — Avni Wadhwani

---

## 1. Prompting notes

**Tool tested:** Gemini
**Transcript:** `../transcripts/gemini_outputs.md`

**Surprises while testing:**

- **It approved its own fake.** IMG-F was generated with Gemini — and in F1 Gemini approved that same AI-generated photo at **100% confidence**. The tool that made the fake could not recognise it.
- **It never actually looked at the photo in F1.** The reasoning says only that *"required photos were attached to support the damage claim"* — the presence of a photo was treated as proof. It missed the heavy wear that contradicts "ripped on day one", which other tools caught.
- **Certainty everywhere.** 100% confidence on 5 of 6 runs, including three wrong decisions (E1, F1, F2), and *"Missing information: none"* on the ambiguous E1 case.
- **It read the customer's words, not the evidence.** In E1 run 2 the reasoning never mentions the photo — the denial rests entirely on the customer's note (*"worn out already after a few weeks"*).
- **It denied for missing evidence while naming the evidence (F2).** It listed *"A photo of the damaged/defective sneakers"* as missing information and still denied at 100% instead of asking for it.
- **It invented a rule about authority (F3).** It told the new team member to *"proceed directly with sending the standard denial email… without needing further manager approval"*, reasoning that only high-value refunds need escalation — treating the absence of a rule as permission.

---

## 2. Speed-dating interview notes

### P1

| Field | Notes |
|---|---|
| Who | Customer — 27+, shops online about once a week |
| Date / format | 8 October 2026, live short-form text interview (5 of the 16 questions, due to interviewee time constraints) |
| First reaction to the concept | "It looks good and fair." (reacting to: clear-cut cases auto-approved, anything unclear plus every denial goes to a human) |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | Not asked — cut from the shortened interview | — |
| Reliability & consistency | Said it would definitely bother them if two people with the same return situation got different outcomes | "Yes, definitely." |
| Latency & performance | Not asked — cut from the shortened interview | — |
| UX friction (human–AI teaming) | Not asked — cut from the shortened interview | — |
| Safety & guardrails | Not asked directly, but their final-say answer implies a human should stay in the loop | — |
| Cost & efficiency | Not asked — cut from the shortened interview | — |

**Who should have the final say (their answer):** Both.

**Most surprising thing they said:** Not a dramatic surprise given the short format, but it was notable that their own last return (a Temu order, returned via USPS) ended in a *partial* refund with no stated reason — the exact kind of unexplained, inconsistent-feeling outcome their C9 answer said would bother them. Their lived experience and their stated principle lined up.

**Caveat:** this interview was shortened to 5 of the 16 questions (C0, C1, C4, C9, C14) to fit the interviewee's available time.

### P2

| Field | Notes |
|---|---|
| Who | Reviewer-like — student, 1.5 years part-time at a campus bookstore & collegiate merchandise e-commerce operation (online order fulfillment, counter returns, web return intake) |
| Date / format | 8 October 2026, live short-form text interview (5 of 19 questions, due to interviewee time constraints) |
| First reaction to the concept | Not asked — cut from the shortened interview |

| Dimension | Notes | Quote |
|---|---|---|
| Accuracy & hallucinations | Not asked — cut from the shortened interview | — |
| Reliability & consistency | Not asked — cut from the shortened interview | — |
| Latency & performance | Not asked — cut from the shortened interview | — |
| UX friction (human–AI teaming) | Would mostly ignore a raw confidence percentage; wants bulleted reasoning behind the decision instead (e.g. photo match, where the tear is, days since delivery) | "Percentages can make people lazy and trick them into hitting 'approve' without actually looking." |
| Safety & guardrails | Reacting to the real "no manager approval needed" AI denial failure: would never act on that recommendation without checking policy and escalating to a shift lead first | "Definitely not... I'd stop, check the original purchase date, review our store's policy manually, and show the case to my shift lead before taking any action." |
| Cost & efficiency | Not asked — cut from the shortened interview | — |

**Who should have the final say (their answer):** Both — the AI as a filter that auto-approves basic, clear-cut returns, but a person always makes the final call on denials or tricky cases.

**Most surprising thing they said:** Not a surprise so much as a direct confirmation — R7 is effectively the real-world version of the Gemini F3 test case documented above (the tool telling a new team member they could send a denial without manager approval). The interviewee's answer, unprompted, was the same conclusion the assignment is built around: a human needs to check policy and escalate before any denial goes out, regardless of how confident the AI sounded.

**Caveat:** this interview was shortened to 5 of the 19 questions to fit the interviewee's available time; dimensions marked "Not asked" were cut, not skipped.

---

## 3. Class-generated storyboard

![ReturnGuard storyboard: a damaged-sneakers return moving through customer submission, data check, policy RAG, image and behavior analysis, AI decision and critic, the human governance gate, and the final decision with an audit log](../../proposal/storyboard.png)

*Class-generated storyboard: a "damaged sneakers" return moving through ReturnGuard. AI can
recommend approval; every denial requires human review.*

**My v1 storyboard.** The fake-photo case (F1) retold through the v1 design: the same
AI-generated image Gemini approved at 100% now fails the separate authenticity check, the
evidence strength drops to Weak, and the gate routes it to a reviewer for a named reason —
an unverified photo can never be auto-approved.

![Avni's ReturnGuard v1 storyboard: nine panels following an AI-generated damage photo — Jordan submits a return with the fake image, a rule-based data check, policy check, photo checks where authenticity is not verified, history check, AI recommendation with Weak evidence, the governance gate routing it to a reviewer, Riley deciding with a confirm step, and Jordan seeing the outcome with a request-a-review option](wadhwani_avni_storyboard_v1.png)

---

## 4. One finding that changed (or confirmed) my assumption about the proposed scenario

The P1 interview **confirmed** the assumption behind ReturnGuard's complementarity split (AI auto-approves clear-cut cases; every denial and anything ambiguous goes to a human). The interviewee's reaction to the concept was unprompted agreement — "it looks good and fair" — and when asked directly who should have the final say, they answered "both," without hesitation.

What strengthens this beyond a generic thumbs-up is their answer to the consistency question: they said it would "definitely" bother them if two people with the identical return situation got different outcomes. That maps onto *trust calibration* from Gonzalez et al. — their trust isn't keyed to the AI being fast or even usually correct, it's keyed to the process being *explainable and uniform*, which is exactly why a fully autonomous, denial-capable AI (like the "proceed with the denial email" failure documented in the prompting notes above) breaks trust even when the underlying decision is correct. Their own most recent return — a Temu order that came back as a partial refund with no stated reason — is a live example of the unexplained-inconsistent-outcome problem they said they didn't like, which suggests the human-reviewed-denial design isn't just theoretically good, it addresses something this user has actually experienced.
