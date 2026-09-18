# Reflections - Trupti Reddy

## Paper 1: Towards a Science of Human-AI Decision Making: A Survey of Empirical Studies

**Full Citation:** Lai, V., Chen, C., Liao, Q. V., Smith-Renner, A., & Tan, C. (2021). *Towards a science of human-AI decision making: A survey of empirical studies.* https://arxiv.org/abs/2112.11471

**Structured Summary:** As AI models get better at prediction, more high-stakes domains (criminal justice, healthcare) are considering AI-assisted decisions, but full automation is usually undesirable there for safety, ethical, and legal reasons, while a fully manual process is slow and error-prone. The authors argue the field needs an empirical science of how humans and AI actually collaborate on decisions, not just better models. They survey over 100 human-subject studies on human-AI decision making and organize the design choices researchers make along three dimensions: the decision task itself, the AI model and what form of assistance it provides, and how success is measured. For each dimension they summarize what most studies currently do, point out where the field's practices are inconsistent or thin, and lay out recommendations for future study design. The paper's main contribution is a shared framework and vocabulary, not a new experiment or a new system.

**Three Key Insights:**
1. Studies of "human-AI decision making" vary wildly in how they measure success, some look at final decision accuracy, others at trust, others at time taken, which makes it hard to compare results across papers unless you're explicit about which one you're targeting.
2. The *form* AI assistance takes (a raw prediction, a confidence score, an explanation, a counter-argument) meaningfully changes how people actually use it; assistance design is its own variable, not a fixed given once you've picked a model.
3. High-stakes domains specifically call for keeping a human in the loop not because the AI is necessarily less accurate, but because of safety, ethical, and legal considerations that sit outside pure model performance, a framing that treats human oversight as a design requirement, not a fallback for a weak model.

**Two Limitations/Risks:**
1. As a survey, it describes what has been studied, not what necessarily works best; it can tell you the field lacks consistent evaluation standards, but it can't tell you which standard to adopt for a system that doesn't yet exist.
2. Most of the underlying studies it surveys involve individual, single-shot decisions (e.g., one prediction, one human review). It's less clear how their findings apply to a multi-stage pipeline like ours, where several AI outputs feed into each other before a human ever sees anything.

**One Concrete Inspiration:** This is direct support for ReturnGuard's Governance Gate design choice. The paper's point that human oversight in high-stakes settings is justified by safety, ethical, and legal concerns independent of model accuracy is exactly the argument for requiring human confirmation on every denial, even ones the pipeline is highly confident about.

---

## Paper 2: Machine Learning for Fraud Detection in E-Commerce: A Research Agenda

**Full Citation:** Tax, N., de Vries, K. J., de Jong, M., Dosoula, N., van den Akker, B., Smith, J., Thuong, O., & Bernardi, L. (2021). *Machine learning for fraud detection in e-commerce: A research agenda.* https://arxiv.org/abs/2107.01979

**Structured Summary:** This paper argues that fraud detection research too often treats it as a pure machine-learning modeling problem, when in practice a fraud-detection model has to operate inside a real organization with real operational constraints. The authors build an "operational model" of how anti-fraud teams at e-commerce companies actually work, and use it to derive six research topics and twelve practical challenges that come up in deployment, not in a lab benchmark. For each topic they summarize what the existing literature does and doesn't cover, and they close by naming twenty-two open research problems the field hasn't solved yet. The paper is a research-agenda/position paper rather than a paper reporting a single new model or experiment.

**Three Key Insights:**
1. A fraud model's accuracy on a static dataset doesn't tell you much about whether it will actually work well once it's deployed inside a team's real review workflow; organizational context changes what "good performance" even means.
2. The paper frames false positives (blocking a legitimate customer) and false negatives (missing real fraud) as a genuine organizational trade-off with real business cost on both sides, not just a metric to optimize in isolation.
3. Because fraud patterns shift as fraudsters adapt to whatever detection method is deployed, a fraud system needs an explicit plan for models going stale. This isn't a one-time training problem.

**Two Limitations/Risks:**
1. As a research-agenda paper, it identifies open problems rather than validated solutions. It tells you what's unsolved, not how to solve it, so it can't be used directly as an implementation reference.
2. The paper is written from the perspective of large e-commerce platforms with substantial existing data and infrastructure. A lot of its assumptions about available historical fraud data may not transfer cleanly to a smaller-scale or newly built system like ours, which has no real labeled fraud history to start from.

**One Concrete Inspiration:** This directly shaped our decision to start ReturnGuard's Behavior agent as a transparent, rule-based risk score instead of a trained ML model. The paper's point about fraud patterns and organizational context shifting over time convinced us that a real trained model without real deployment data would be false rigor, and an explainable rule-based score is the more honest starting point we can later upgrade.
