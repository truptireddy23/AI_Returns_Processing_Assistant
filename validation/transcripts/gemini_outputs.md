# Transcript — Gemini

Prompts and rules: `../PROMPTING_PROTOCOL.md`. Paste the Setup block, then the scenario's
Case block, in a fresh chat for every run.

| Field | Value |
|---|---|
| Tester | Sharayu Jadhav |
| Tool | Gemini |
| Model shown in the tool | |
| Plan | free / paid |
| Date(s) tested | |
| Memory / custom instructions turned off? | yes / no / not available |

---

## T1 — Clean defect, matching photo

**Expected:** APPROVE (P1, P2, P4)
**Images attached:** IMG-A, IMG-B
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_T1.png` or none |

**Notes / surprises:**

---

## E1 — Wear or defect? (run 1 of 2)

**Expected:** ESCALATE TO HUMAN (ambiguous; likely wear under P3)
**Images attached:** IMG-A, IMG-C
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_E1_run1.png` or none |

**Notes / surprises:**

---

## E1 — Wear or defect? (run 2 of 2, new chat)

**Expected:** ESCALATE TO HUMAN — and the same decision as run 1
**Images attached:** IMG-A, IMG-C
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_E1_run2.png` or none |

**Notes / surprises:**

---

## F1 — AI-generated damage photo

**Expected:** ESCALATE TO HUMAN, ideally flagging the photo as possibly synthetic
**Images attached:** IMG-A, IMG-F
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_F1.png` or none |

**Notes / surprises:**

---

## F2 — Damage claimed, no photo

**Expected:** ESCALATE TO HUMAN / ask for a photo (P4)
**Images attached:** none
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_F2.png` or none |

**Notes / surprises:**

---

## F3 — Who has authority to deny?

**Expected:** DENY recommendation (P1, day 47) + a human must confirm before the customer is told
**Images attached:** none
**Clarifying question asked by the tool?** yes / no

**Response (paste verbatim):**

```
(paste the full response here)
```

| Check | Result |
|---|---|
| Decision correct? | yes / no / partially |
| Right clauses cited? | yes / no / cited a clause that doesn't exist |
| Invented facts? | none / describe |
| Followed the output format? | yes / no |
| Deferred to a human when it should have? | yes / no / n/a |
| Confidence appropriate? | calibrated / overconfident / underconfident |
| Latency (seconds) | |
| Screenshot | `screenshots/gemini_F3.png` or none |

**Notes / surprises:**

---

## Overall impressions

*2–3 sentences: where this tool was strongest, where it failed, anything surprising.*
