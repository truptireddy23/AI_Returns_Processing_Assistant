# ReturnGuard - AI Returns Processing Assistant
A human centered Generative AI system that helps consumers navigate product returns, understand policies, and complete return related tasks.

---

## Table of Contents

- [Team Members & Roles](#team-members--roles)
- [Problem Statement & Motivation](#problem-statement--motivation)
- [Target Users & Core Tasks](#target-users--core-tasks)
- [Competitive Landscape](#competitive-landscape)
- [Initial Concept & Value Proposition](#initial-concept--value-proposition)
- [Milestones Roadmap](#milestones-roadmap)
- [Repository Structure](#repository-structure)

---

## Team Members & Roles

| Name | Domain Responsibility | Contact |
|---|---|---|
| Aditya Kamath | Systems & AI Architecture — LangGraph pipeline design, governance integration (OPA/ContextForge), infrastructure | kamath6@illinois.edu |
| Trupti Reddy | Frontend — Next.js shop interface and reviewer dashboard | tdreddy2@illinois.edu |
| Avni Wadhwani | ML/Data — risk model, image matching, and policy RAG | avniw2@illinois.edu |
| Sharayu Jadhav | Literature Review, Evaluation & QA — research synthesis, testing, and evaluation | sjadhav5@illinois.edu |


---

## Problem Statement & Motivation

Every return an online retailer receives forces a judgment call: is this a legitimate return, or fraud and policy abuse? Getting that call wrong is costly in both directions — wave abuse through and it erodes margins; wrongly deny a legitimate customer and it erodes trust and loyalty. Both sides of that tension are documented in the industry's own numbers.

**Scale and cost**
- Total U.S. retail returns are projected to reach **$849.9B in 2025** — **15.8%** of total annual sales — up from $309B in 2019, as returns have shifted from a back-office cost to a central driver of retail profitability.
- Online orders return at a much higher rate than the overall average: **19.3%** of e-commerce sales are expected to be returned in 2025.

**Fraud and abuse**
- **9%** of all returns are estimated to be outright fraudulent (excluding bracketing and wardrobing) — nearly 1 in every 10.
- **62%** of consumers admit to at least one return behavior that is costly to retailers or abuses their policies (bracketing, wardrobing, decoy returns, empty-box claims), and **45%** say it's acceptable to "bend the rules" when returning items — rising to 66% among Gen Z.
- Fraud is also getting more sophisticated: retailers rank overstated return quantities, decoy/counterfeit items, empty-box ("box of rocks") returns, and label/tracking-ID tampering among the most prevalent tactics they track.

**The customer-trust side of the same coin**
- **57%** of shoppers say they will stop shopping with a retailer after being charged for a return — up sharply from 40% in 2024.
- **71%** say a poor returns experience makes them less likely to shop with that retailer again (up from 67%), and 80% tell friends and family about a bad returns experience.
- **72%** of merchants now charge for at least one return method to manage cost and fraud (up from 66% in 2024) — but of those, 47% report an increase in customer complaints and 37% report losing customers over it.

**Where current tools fall short**
- **85%** of merchants already use AI/ML somewhere in their returns process to detect fraud — but only **45%** consider it truly effective on its own, and 40% call the results mixed. Automated fraud tooling is already widespread; it is not yet solving the problem.

*Source: National Retail Federation (NRF) & Happy Returns, a UPS Company, [2025 Retail Returns Landscape](https://nrf.com/research/2025-retail-returns-landscape) (fielded Aug–Sep 2025; n=2,006 consumers, n=358 merchant professionals at $500M+ revenue companies).*

Today, this judgment call is handled one of two ways, and both fail: **manual review** doesn't scale and is inconsistent across reviewers, while **rule-based policy engines** are too rigid to weigh nuanced evidence (photos, free-text reasons, order history) and end up punishing honest edge cases. Neither approach produces a record that holds up when a customer disputes a decision.

This matters *now* because the data shows both sides of the tension worsening at once: return volume, fraud sophistication, and consumers' own tolerance for "bending the rules" are all rising — while customer sensitivity to being wrongly charged or denied is rising even faster (57% walk away after a return fee, up from 40% in just one year). Retailers are not ignoring this: 85% already use AI somewhere in their fraud process. The gap is that those tools aren't explainable, aren't governed, and aren't reliably effective (only 45% rate them so). That's precisely the gap ReturnGuard is built to close — a system that reasons over the same nuanced evidence a skilled reviewer would, but does so consistently, explainably, and with a human still accountable for every denial.

---

## Target Users & Core Tasks

**Primary personas:**

1. **Trust & Safety Reviewer** — the internal analyst who triages flagged returns. Needs to move fast, but needs a clear, evidence-based explanation to act on rather than an opaque score.
2. **Customer** — the person submitting the return. Wants a quick, fair decision, and a guarantee that a real person reviews it if they're denied.
3. **Risk / Platform Team** — owns the return policy and compliance posture. Needs every automated decision to be policy-compliant, consistent, and auditable after the fact.

**Top tasks these users accomplish with ReturnGuard:**

1. **Submit and track a return** — a customer submits item, reason, and photo evidence, and gets a fast, explained decision.
2. **Review and resolve a flagged case** — a Trust & Safety reviewer opens a case the system routed to them (any denial), sees the full evidence trail and AI-generated rationale, and confirms or overturns it.
3. **Audit a past decision** — a risk/platform team member traces exactly which policy, evidence, and reasoning produced a given decision, end to end.

---

## Competitive Landscape

| Approach | How it works | Shortcomings |
|---|---|---|
| **Manual review queues** | Human agents eyeball flagged returns using judgment and a policy document. | Slow, doesn't scale with volume spikes (e.g. holidays); inconsistent across reviewers; no structured audit trail. |
| **Rule-based policy engines** | Hard-coded thresholds — e.g. "deny if return window > 30 days." | Can't weigh photo or behavioral evidence; rigid and punishes honest edge cases; produces no reasoning a customer can appeal to. |
| **Black-box fraud-scoring SaaS** | A vendor-supplied ML risk score gates the approve/deny decision. | Opaque — no human-readable rationale; typically no human-in-the-loop on denials; bias/fairness risk goes unchecked. |

None of these combine (a) reasoning over multi-modal, unstructured evidence, (b) an explainable, appealable rationale, and (c) a hard governance guarantee that a human confirms every denial. That combination is ReturnGuard's gap to fill — see `/literature/` for the supporting research and full citations.

---

## Initial Concept & Value Proposition

**ReturnGuard** is a governed multi-agent system that reviews e-commerce returns for fraud and policy violations using retrieval-grounded policy checks, image and behavioral analysis, and a human-in-the-loop safeguard on every denial — with full auditability built in.

**How a return moves through the system:**

A submitted return flows through a LangGraph pipeline of specialist agents: a **Data-Quality Gate** and **Planner** prepare the case, **Intake** structures it, **Policy (RAG)** checks it against the retrieved return policy, **Image** analyzes photo evidence (CLIP matching, AI-generated image detection), and **Behavior** scores return-history risk. A **Decision** agent synthesizes all of this into a verdict, a **Critic** agent reviews that reasoning for errors, and an **Explanation** agent produces a human-readable rationale. Every decision then passes through a **Governance Gate**: approvals can flow through automatically, but every denial is held for human confirmation before it's final.

**Why this needs GenAI, not a rules engine:**

- It reasons over unstructured evidence — photos, free-text reasons, order notes — that rule sets can't parse.
- It weighs several weak, sometimes-conflicting signals (policy fit, image match, behavioral risk) into a single judgment call.
- It produces a natural-language rationale for every decision, making it explainable and appealable rather than a bare score.

**Governance and auditability, by design:**

Every tool and model call the agents make is checked against **OPA (Open Policy Agent)**, which fails closed — if a policy check errors out, the default is to block, not allow. **IBM ContextForge** governs tool orchestration at the MCP level. Combined with mandatory human review on every denial, the system is designed so AI can approve autonomously but can never unilaterally deny a customer. A hash-chained, append-only audit log (Postgres) plus tracing (Langfuse) and metrics (Prometheus/Grafana) make every decision inspectable after the fact — full architecture in `/proposal/PROPOSAL.md` and the system diagram below.

---

## Milestones Roadmap

| Checkpoint | Target | Key Deliverables |
|---|---|---|
| **Checkpoint 1** (this deliverable) | Project kickoff | Problem definition, literature review (8+ papers), formal proposal, GitHub repo structure, slide deck |
| **Checkpoint 2** | Prototype validation | Core LangGraph pipeline (Intake → Policy RAG → Image → Behavior → Decision) running end-to-end on test cases; initial governance wiring (OPA fail-closed checks) |
| **Checkpoint 3** | System integration | Full pipeline incl. Critic + Explanation agents; Governance Gate with human-in-the-loop review UI; observability (Langfuse, Prometheus, Grafana) wired in |
| **Checkpoint 4** | Final delivery | End-to-end demo on realistic return scenarios; audit-log/traceability walkthrough; evaluation results and final report |

---

## Repository Structure

```
├── README.md               # This file — project landing page
├── /literature/             # Research papers & citation bibliography (8+ papers)
├── /reflections/             # Individual reflections (lastname_firstname.md)
├── /proposal/
│   └── PROPOSAL.md          # Formal 500–800 word project proposal
└── (GitHub Projects & Issues) # Task assignment & milestone tracking
```
