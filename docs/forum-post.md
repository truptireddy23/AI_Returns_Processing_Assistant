# ReturnGuard: Checkpoint 3 submission draft

Team: Aditya Kamath, Trupti Reddy, Avni Wadhwani and Sharayu Jadhav.

Repository: https://github.com/truptireddy23/AI_Returns_Processing_Assistant

ReturnGuard reviews e-commerce return requests with real model inference and a code
policy gate. Customers can submit evidence and request another review. Reviewers inspect
policy citations, photo findings and behavior risk, then own every denial. Admins control
automation limits and audit outcomes.

The implementation includes model policy tools, streamed reviewer traces, input masking,
usage/cost telemetry and an offline behavior-risk group audit. Setup is in `app/INSTALL.md`.
Architecture, use cases, safety and observability are in `docs/`. Verification details and
limits are in `docs/evaluation/CP3_VERIFICATION.md`.

Our CP4 plan uses Track B: a held-out algorithmic benchmark comparing deterministic
steps and model steps on routing accuracy, unsafe approvals, escalation, latency and
observed token usage. Synthetic group checks are not evidence of population fairness.

Presentation and backup recording should be attached separately before submission.
