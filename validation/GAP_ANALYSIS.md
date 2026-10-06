# Gap Analysis

Empirical gaps from the prompting study (`PROMPTING_PROTOCOL.md`, `transcripts/`) and the
speed-dating interviews, each read through the complementarity lens of Gonzalez et al.
(2026).

---

## 1. Gap matrix

*To be completed in Step 5, once transcripts and interview notes are in.*

| Dimension | Empirical failure (quote / link to receipt) | Theoretical reading |
|---|---|---|
| Accuracy & hallucinations | | |
| Reliability & consistency | | |
| Latency & performance | | |
| UX friction (human–AI teaming) | | |
| Safety & guardrails | | |
| Cost & efficiency | | |

---

## 2. Method — speed-dating interviews (Step 4)

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
