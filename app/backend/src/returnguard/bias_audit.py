"""Offline risk audit: CSV group labels are supplied explicitly, never inferred.

python -m returnguard.bias_audit input.csv --reference group_a
Exit 1 flags a risk-pass rate ratio below threshold, 2 means invalid data.
A screen is neither a legal conclusion nor proof of fairness.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from returnguard.pipeline.behavior import BehaviorInputs, score_behavior


def audit_rows(
    rows: list[dict[str, str]],
    *,
    reference: str,
    risk_limit: float = 0.5,
    ratio_threshold: float = 0.8,
    min_group_size: int = 20,
) -> dict[str, Any]:
    if not 0 <= risk_limit <= 1 or not 0 < ratio_threshold <= 1 or min_group_size < 1:
        raise ValueError("Invalid threshold or minimum group size")
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        group = row.get("group", "").strip()
        if not group:
            raise ValueError("Every row needs an explicit group label")
        inputs = BehaviorInputs(**{f.name: int(row[f.name]) for f in fields(BehaviorInputs)})
        if any(v < 0 for v in asdict(inputs).values()) or inputs.high_value_limit_cents <= 0:
            raise ValueError("Inputs must be nonnegative; high-value limit must be positive")
        groups[group].append(score_behavior(inputs).score)
    if reference not in groups or len(groups) < 2:
        raise ValueError("Need a populated reference and at least one comparison group")
    rates = {g: sum(s < risk_limit for s in scores) / len(scores) for g, scores in groups.items()}
    base = rates[reference]
    summaries: dict[str, Any] = {}
    for group, scores in sorted(groups.items()):
        ratio = rates[group] / base if base > 0 else None
        summaries[group] = {
            "n": len(scores),
            "mean_risk": round(sum(scores) / len(scores), 6),
            "risk_pass_rate": rates[group],
            "risk_flag_rate": 1 - rates[group],
            "pass_rate_ratio": ratio,
            "screen_flag": ratio is not None and ratio < ratio_threshold,
            "small_sample": len(scores) < min_group_size,
        }
    return {
        "reference": reference,
        "risk_limit": risk_limit,
        "ratio_threshold": ratio_threshold,
        "groups": summaries,
        "flagged": any(g["screen_flag"] for g in summaries.values()),
        "warnings": [
            "Descriptive risk-only screening, not final decision fairness or causal evidence.",
            "Synthetic or small samples cannot establish population fairness.",
        ]
        + (["Reference pass rate is zero: ratios are undefined."] if base == 0 else []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv", type=Path, help="group," + ",".join(f.name for f in fields(BehaviorInputs))
    )
    parser.add_argument("--reference", required=True)
    parser.add_argument("--risk-limit", type=float, default=0.5)
    parser.add_argument("--ratio-threshold", type=float, default=0.8)
    parser.add_argument("--min-group-size", type=int, default=20)
    args = parser.parse_args()
    try:
        with args.csv.open(newline="") as source:
            report = audit_rows(
                list(csv.DictReader(source)),
                reference=args.reference,
                risk_limit=args.risk_limit,
                ratio_threshold=args.ratio_threshold,
                min_group_size=args.min_group_size,
            )
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    sys.exit(1 if report["flagged"] else 0)


if __name__ == "__main__":
    main()
