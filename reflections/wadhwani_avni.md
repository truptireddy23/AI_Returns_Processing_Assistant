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
