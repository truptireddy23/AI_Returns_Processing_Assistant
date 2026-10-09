# Reflections — Avni Wadhwani

## Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

**1. Full Citation & Link**

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. In *Advances in Neural Information Processing Systems* (Vol. 33, pp. 9459–9474). https://arxiv.org/abs/2005.11401

**2. Structured Summary**

Lewis et al. (2020) address a fundamental limitation of large pre-trained language models: although such models encode substantial factual knowledge within their parameters, this knowledge is static, difficult to attribute to a source, and prone to fabrication on knowledge-intensive tasks. The authors propose Retrieval-Augmented Generation (RAG), a hybrid architecture that couples a parametric sequence-to-sequence generator (BART) with a non-parametric memory consisting of a dense vector index of Wikipedia, queried at inference time by a Dense Passage Retrieval (DPR) component. Retrieved passages condition the generator, and the retriever's query encoder and the generator are fine-tuned jointly; the authors evaluate two formulations—RAG-Sequence, which conditions on a single set of documents for the entire output, and RAG-Token, which marginalizes over documents at each generated token. Empirically, RAG establishes state-of-the-art results on three open-domain question-answering benchmarks and produces more specific, diverse, and factually grounded text than a parametric-only baseline. A particularly consequential finding is that the model's knowledge resides in a replaceable index, permitting knowledge to be updated by modifying the index rather than retraining the underlying model.

**3. Three Key Insights**

1. Decoupling knowledge storage (a retrievable index) from generation (the parametric model) enables provenance, auditability, and knowledge updates independent of model weights—a property with significant implications for any system required to justify its outputs.
2. Retrieval quality is not incidental to performance: jointly optimizing the retriever's query encoder with the generator allows the model to learn to exploit retrieved evidence, outperforming pipelines that append retrieval to a frozen generator.
3. Grounding generation in retrieved evidence constitutes a concrete and measurable mechanism for mitigating hallucination, since outputs are conditioned on verifiable source passages rather than on parametric memory alone.

**4. Two Limitations or Risks**

1. The architecture's reliability is bounded by retrieval performance. When a relevant passage is absent from the index or ranked poorly, the generator may still produce a fluent and confident yet incorrect response; because such failures are not signaled to the user, they present a substantial risk in high-stakes decision contexts.
2. RAG retrieves a fixed number of passages irrespective of necessity or relevance, and provides no mechanism to verify that a generated output is actually entailed by the retrieved evidence, allowing irrelevant context to influence generation without detection.

**5. One Concrete Inspiration**

This architecture directly informs the design of our Policy agent. Return policies are stored in the Qdrant vector index, and each policy determination is conditioned on the specific clause retrieved for the case under review; policy revisions therefore require only an update to the index rather than retraining of the model. Furthermore, because each decision is grounded in an identifiable retrieved clause, that clause can be recorded in the audit log, supplying the evidentiary basis necessary for a denial to be explained and contested rather than issued opaquely.

---

## Paper 2: Trust, Distrust, and Appropriate Reliance in (X)AI: A Survey of Empirical Evaluation of User Trust

**1. Full Citation & Link**

Visser, R., Peters, T. M., Scharlau, I., & Hammer, B. (2023). Trust, distrust, and appropriate reliance in (X)AI: A survey of empirical evaluation of user trust. Presented at the 1st xAI World Conference (Lisbon, Portugal). https://arxiv.org/abs/2312.02034

**2. Structured Summary**

Visser et al. (2023) address the widely assumed but empirically shaky premise that explainable AI (XAI) increases user trust — what they term the "explainability-trust hypothesis." Drawing on machine learning, human-computer interaction, and organizational psychology, the authors first clarify terminology that is routinely conflated in the XAI literature: trust is an attitude a user holds toward a system, distinct from trustworthiness, which is a property of the system itself (its competence, benevolence, and integrity, per Mayer et al.'s 1995 model). Because users cannot observe a system's actual trustworthiness directly, they rely on observable "cues" (Schlicker & Langer, 2021) — including explanations — to form a perception of trustworthiness, and the goal of good system design is "appropriate reliance": avoiding both disuse (not relying on a system that is in fact correct) and overtrust (relying on a system that is in fact wrong). The paper's second contribution is a structured survey of roughly 40 empirical studies that measure the effect of XAI methods on user trust, categorized by application domain, the type of model descriptor or explanation shown, the measurement method used (self-report, behavioral, or physiological), and the outcome reported. The survey's central finding is that results are mixed: self-reported trust usually rises with the addition of an explanation, but behavioral measures of actual reliance frequently show no effect, a negative effect, or an increase in reliance on predictions that are wrong — i.e., overtrust. The authors also argue for treating distrust as a separate dimension from trust rather than its mere inverse, since distrust has been empirically linked to beneficial effects such as increased creativity, improved memory for detail, and more critical scrutiny of a system's outputs — benefits that are invisible to research that treats "more trust" as the only desirable outcome.

**3. Three Key Insights**

1. Explanations and confidence displays do not reliably produce calibrated trust — several of the surveyed studies found that showing an explanation increased users' reliance on incorrect predictions, meaning an explanation can manufacture false confidence as easily as justified confidence.
2. Trust and distrust are better modeled as two separate dimensions than as opposite ends of one scale, because a user can simultaneously trust a system in some respects while appropriately distrusting it in others, and distrust itself serves a protective, scrutiny-inducing function that pure trust-building design suppresses.
3. Because actual trustworthiness is not directly observable, a user's perceived trustworthiness is only as accurate as the cues a system exposes — a system that visibly explains what it checked and what it is unsure about gives users better material to calibrate against than one that merely asserts a confidence number.

**4. Two Limitations or Risks**

1. The survey is explicitly narrative and conceptual rather than a systematic review with a reproducible search and inclusion protocol, so its coverage of the empirical literature, while extensive, is not guaranteed to be exhaustive or free of selection bias.
2. The paper's own recommendation — adopting Rusk's (2018) separate trust/distrust scale to address the field's reliance on unvalidated, ad hoc self-report instruments — rests on a scale the original author says still needs independent validation; the proposed fix inherits the same unresolved measurement problem it is meant to solve.

**5. One Concrete Inspiration**

This paper is the direct evidentiary basis for ReturnGuard's decision to never show a model's self-rated confidence percentage to a reviewer. Visser et al.'s finding that explanations and confidence cues can increase reliance on wrong predictions matches exactly what our own prompting study showed — Gemini and the other tools stated 95-100% confidence on three wrong decisions (E1, F1, F2) — and it is why the case page instead shows an **evidence strength** computed from the underlying checks (Strong / Mixed / Weak) plus an explicit **"Uncertain about"** list in plain language. Treating distrust as a productive, separate signal rather than a deficiency also shapes the photo authenticity check: a photo that fails verification is surfaced as its own warning, not folded into an overall score, so that the reviewer's skepticism is triggered by a specific, named cue rather than a single blended number that could paper over it.
