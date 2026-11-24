# Benchmark results

32 labelled cases; expected routes: Auto-approved 7, Person 20, Back to customer 5.

| Metric | Rules only (baseline) | AI pipeline (full) |
|---|---|---|
| Cases scored | 32 | 32 |
| Route accuracy | 90.6% (29/32) | 93.8% (30/32) |
| Unsafe auto-approvals | 2 | 2 |
| Missed automations | 1 | 0 |
| Automatic denials | 0 | 0 |
| Needs-a-person F1 (P / R) | 0.939 (0.958 / 0.92) | 0.958 (1.0 / 0.92) |
| Automation rate | 25.0% | 28.1% |
| Escalation rate | 59.4% | 56.2% |
| AI proposal acceptable | 88.9% (n=27) | 92.6% (n=27) |
| Photo verdict accuracy | 50.0% (n=10) | 80.0% (n=10) |
| Route accuracy 95% CI (Wilson) | 75.8 to 96.8% | 79.9 to 98.3% |
| Exact McNemar p vs rules | n/a | 1.0 |
| Latency p50 / p95 (s), incl. free-tier throttling | n/a | 29.3 / 76.4 (n=26) |
| Tokens in / out (total) | 0 / 0 | 129,529 / 8,873 |
| Mean tokens per AI case | 0 | 5,126 |
| Pipeline errors | 0 | 0 |

## Cases routed differently from the label

- **Rules only (baseline)**: `defect-real-sole`, `cm-worn-shorts`, `cm-worn-slipons`
- **AI pipeline (full)**: `photo-ai-generated`, `nad-material`
