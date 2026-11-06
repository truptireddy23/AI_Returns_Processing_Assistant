# Behavior-risk group audit

Run `make bias-audit` from `app/`. The committed example report comes from eight matched
synthetic profiles in `tests/fixtures/behavior_groups.csv`. Each group has the same four
behavior profiles, so equal scores and risk-pass rates are expected. This verifies the
screening workflow, not population fairness.

For a real evaluation, supply a CSV with `group` and the seven `BehaviorInputs` fields:
`past_orders`, `past_returns`, `recent_returns_30d`, `account_age_days`,
`other_accounts_at_address`, `refund_cents`, `high_value_limit_cents`.
Use documented, appropriately collected group labels. Never infer protected attributes
from names or addresses. Keep person-level audit data outside git.

From `app/backend`:

```bash
uv run python -m returnguard.bias_audit /path/to/audit.csv --reference reference_group \
  --risk-limit 0.5 --ratio-threshold 0.8 --min-group-size 20
```

The default 0.8 ratio is an adjustable screening threshold, not a legal test or fairness
guarantee. Scores at or above the risk limit fail the risk check. The report compares the
share passing that check against the supplied reference. It flags small groups and
undefined ratios, without making significance or causal claims. Investigate data mix,
shared-address and account-age effects when groups differ. Passing a risk check does
not imply that the complete governance gate approves a return.

Exit codes: 0 means no ratio fell below threshold, 1 means a screening flag, 2 means
invalid input. A zero exit status with small synthetic samples is not evidence of
real-world fairness. CP4 should evaluate held-out routing outcomes and representative
data, including subgroup uncertainty where sufficient data exists.
