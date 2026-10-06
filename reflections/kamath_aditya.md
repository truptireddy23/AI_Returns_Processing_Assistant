# Individual Reflection — Kamath Aditya

---

## 1. Policy-as-Prompt: Turning AI Governance Rules into Guardrails for AI Agents

**Full Citation & Link:** Kholkar, G., & Ahuja, R. (2025). *Policy-as-Prompt: Turning AI governance rules into guardrails for AI agents.* Presented at the Workshop on Regulatable ML, 39th Conference on Neural Information Processing Systems (NeurIPS 2025). https://arxiv.org/abs/2509.23994

**Structured Summary:** This paper names a practical problem every regulated AI deployment runs into: a governance rule that's easy to state in a design document (a PRD, a security policy) is hard to turn into something an AI agent actually enforces at runtime — the "policy-to-practice gap." Their two-stage framework, Policy-as-Prompt, first uses an LLM (Policy-Tree-Gen) to parse unstructured design artifacts and classify each extracted rule into one of four categories, anchoring every rule to real examples already present in the source document rather than invented ones. The second stage (Policy-as-Prompt-Gen) compiles the verified rule tree into a human-readable prompt that a lightweight LLM uses at runtime as a real-time compliance judge, defaulting to block on anything out-of-domain. Every generated guardrail is reviewed and approved by a human security engineer before deployment. Tested on real internal HR and Security Operations Center use cases, runtime enforcement reached roughly 70–73% accuracy — framed by the authors not as a finished solution, but as a valuable first-line, default-deny filter that reduces the attack surface while still routing ambiguous cases to a human.

**Three Key Insights:**
1. Governance in agentic AI systems isn't just a runtime concern — this paper puts a human checkpoint at the *policy-authoring* stage too, meaning the rules themselves get reviewed before they're ever enforced, not just the decisions the rules produce.
2. The authors are explicit that a guardrail doesn't need to be highly accurate to be worth deploying — a default-deny, fail-closed filter is valuable even at ~70% accuracy *because* uncertain or unclear cases still escalate to a human rather than passing silently.
3. Treating policy documents (PRDs, technical specs) as the direct source of truth for what an AI agent is allowed to do — rather than hand-writing separate enforcement logic — is a scalable way to keep governance rules synchronized with what the business actually documented.

**Two Limitations or Risks:**
1. The paper is candid about its own weak points: policy-extraction quality (Macro-F1) was as low as 24.5% for the best model on the HR domain, and the framework leans heavily on large proprietary models — open-source alternatives performed noticeably worse, which raises cost and vendor-lock-in concerns for adoption.
2. Both evaluation domains (HR, SOC) are internal enterprise workflows with modest, non-public gold datasets (100 examples each); there's no evidence in the paper that this approach generalizes to a customer-facing, adversarial domain like e-commerce returns, where the "policy" also has to survive users actively trying to get around it.

**One Concrete Inspiration:** Beyond using this pattern for OPA policy generation, apply the paper's *authoring-stage* human checkpoint to ReturnGuard specifically: when the Policy RAG agent's underlying return-policy document changes, auto-diff the extracted policy rules and require a Risk/Platform team member to explicitly re-approve only the *changed* rules — rather than re-approving the whole policy corpus every time, which would quickly become a rubber-stamp exercise nobody actually reads.

---

## 2. Methods and Trends in Detecting AI-Generated Images: A Comprehensive Review

**Full Citation & Link:** Mahara, A., & Rishe, N. (2025). *Methods and trends in detecting generated images: A comprehensive review.* arXiv. https://arxiv.org/abs/2502.15176

**Structured Summary:** The paper addresses a fast-growing problem: as GANs, diffusion models, and VAEs make synthetic images increasingly hard to distinguish from real ones, the risk of adversarial misuse — including fabricated "proof" images — has grown alongside them, while prior surveys have mostly focused narrowly on deepfake (face-swap) detection and missed recent, more general advances. This survey systematically reviews synthetic-image detection methods and organizes them into six paradigms: spatial-domain, frequency-domain, fingerprint-based, patch-based, training-free, and multimodal reasoning-based approaches. It then runs comparative analysis of these method families across public benchmark datasets, specifically evaluating them on generalizability (do they work on generators they weren't trained on), robustness (do they survive compression/cropping/re-editing), and interpretability (can a human understand why the model flagged an image). The authors conclude that no single paradigm dominates on all three axes, and argue the most promising direction forward is hybrid detectors that combine the speed of training-free methods with the semantic reasoning of multimodal (vision-language) models — aiming for detection that is both accurate and explainable.

**Three Key Insights:**
1. Detection method families trade off differently on generalizability vs. interpretability — a fast, training-free detector may not explain *why* it flagged an image, while a multimodal reasoning-based one can, which matters directly for a system that needs to justify a denial to a customer.
2. No detector generalizes perfectly across generator types, meaning a purpose-built image-fraud pipeline should expect built-in blind spots against generative models newer than whatever the detector was validated on, not treat detection as a solved, static problem.
3. Robustness to real-world image manipulation (compression, cropping, resaving) is evaluated as a distinct axis from raw detection accuracy — a detector that performs well on clean benchmark images can still fail on a photo a customer re-compressed by texting it to themselves before uploading.

**Two Limitations or Risks:**
1. As a survey, the paper reports how existing methods perform on published benchmarks, not on a returns/e-commerce-specific dataset — there is no evidence here that any of these detectors have been validated on the kind of casual, low-quality photos customers actually submit with a return.
2. The paper itself flags that this field is still maturing — the "best" approach it points to (hybrid training-free + multimodal reasoning) is described as a future direction, not an established, off-the-shelf solution, meaning ReturnGuard's Image agent is building on an open research problem, not a solved one.

**One Concrete Inspiration:** Rather than relying on a single detection paradigm, design the Image agent to combine a fast training-free detector as a first-pass filter with a multimodal reasoning-based check (paired with the CLIP-based match already planned) specifically on borderline cases — giving the Explanation agent an actual textual rationale for an image-fraud flag instead of an opaque confidence score, consistent with what this survey identifies as the field's main open gap.
