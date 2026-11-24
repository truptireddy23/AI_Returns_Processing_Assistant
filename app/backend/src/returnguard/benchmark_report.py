# ruff: noqa: E501  (SVG markup is clearer on one line)
"""Score the CP4 benchmark results and draw the figures (standard library only).

    python -m returnguard.benchmark_report [--usd-in 0.29 --usd-out 0.59]

Reads docs/study_materials/benchmark/{cases.json,results/*.jsonl}; writes
docs/study_materials/benchmark/{summary.json,RESULTS.md} and docs/figures/*.svg.
Token prices are optional (USD per million tokens); without them, cost is reported
in tokens only.
"""

import argparse
import collections
import html
import json
import math
import statistics
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
BENCH = REPO / "docs" / "study_materials" / "benchmark"
FIG = REPO / "docs" / "figures"

ORDER = ["rules", "model", "model_no_critic", "model_no_tools"]
LABEL = {
    "rules": "Rules only (baseline)",
    "model": "AI pipeline (full)",
    "model_no_critic": "AI pipeline, no critic",
    "model_no_tools": "AI pipeline, no policy tools",
}
COLOR = {
    "rules": "#64748b",
    "model": "#4f46e5",
    "model_no_critic": "#0891b2",
    "model_no_tools": "#d97706",
}
ROUTES = ["auto_approved", "reviewer", "customer"]
ROUTE_LABEL = {
    "auto_approved": "Auto-approved",
    "reviewer": "Person",
    "customer": "Back to customer",
}
MODEL_STEPS = ["policy", "image", "recommendation", "critic"]


def load() -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    spec = json.loads((BENCH / "cases.json").read_text())
    cases = {c["key"]: c for c in spec["cases"]}
    results: dict[str, list[dict[str, Any]]] = {}
    for path in sorted((BENCH / "results").glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        results[path.stem] = [r for r in rows if r["case"] in cases]
    return cases, results


def pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 1) if b else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo), 1)


def wilson(x: int, n: int, z: float = 1.96) -> list[float] | None:
    """95% Wilson score interval for a proportion, in percent."""
    if not n:
        return None
    q, d = x / n, 1 + z * z / n
    centre = (q + z * z / (2 * n)) / d
    half = z * math.sqrt(q * (1 - q) / n + z * z / (4 * n * n)) / d
    return [round(100 * (centre - half), 1), round(100 * (centre + half), 1)]


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Two-sided exact McNemar p-value from the two discordant counts."""
    n: int = only_a + only_b
    k: int = min(only_a, only_b)
    if n == 0:
        return 1.0
    p: float = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return round(min(1.0, p), 4)


def slept(row: dict[str, Any]) -> bool:
    """The step clock (wall time) ran well past the process clock (pauses in sleep)."""
    steps_ms = sum((s.get("latency_ms") or 0) for s in row["steps"].values())
    return bool(steps_ms > row["wall_ms"] * 1.1 + 1000)


def tokens(row: dict[str, Any]) -> tuple[int, int]:
    ti = sum((s.get("tokens_in") or 0) for s in row["steps"].values())
    to = sum((s.get("tokens_out") or 0) for s in row["steps"].values())
    return ti, to


def score_variant(
    cases: dict[str, dict[str, Any]], rows: list[dict[str, Any]], usd: tuple[float, float] | None
) -> dict[str, Any]:
    first = [r for r in rows if r["repeat"] == 1]
    n = len(first)
    exp = {k: c["expected"] for k, c in cases.items()}
    correct = sum(r["route"] == exp[r["case"]]["route"] for r in first)
    unsafe = [
        r["case"]
        for r in first
        if r["route"] == "auto_approved" and exp[r["case"]]["route"] != "auto_approved"
    ]
    missed = [
        r["case"]
        for r in first
        if exp[r["case"]]["route"] == "auto_approved" and r["route"] != "auto_approved"
    ]
    auto_denials = sum(
        1 for r in first if r["final_decision"] == "deny" and r["decided_by_type"] == "auto"
    )
    errors = [r["case"] for r in first if r["error"]]

    # "Needs a person or the customer" as the positive class.
    tp = sum(
        1
        for r in first
        if exp[r["case"]]["route"] != "auto_approved" and r["route"] != "auto_approved"
    )
    fp = sum(
        1
        for r in first
        if exp[r["case"]]["route"] == "auto_approved" and r["route"] != "auto_approved"
    )
    fn = len(unsafe)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None

    proposal_rows = [r for r in first if exp[r["case"]]["proposal"]]
    proposal_ok = sum(1 for r in proposal_rows if r["ai_proposal"] in exp[r["case"]]["proposal"])
    photo_rows = [r for r in first if exp[r["case"]]["photo"] in ("verified", "not_verified")]
    photo_ok = sum(
        1
        for r in photo_rows
        if (r["steps"].get("image") or {}).get("check") == exp[r["case"]]["photo"]
    )

    confusion = {e: {a: 0 for a in ROUTES} for e in ROUTES}
    for r in first:
        confusion[exp[r["case"]]["route"]][r["route"] or "reviewer"] += 1

    by_cat: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for r in first:
        by_cat[r["category"]][0] += int(r["route"] == exp[r["case"]]["route"])
        by_cat[r["category"]][1] += 1

    # Latency: AI cases only, and not those where the machine slept mid-case.
    timed = [r for r in first if sum(tokens(r)) > 0 and not slept(r)]
    walls = [r["wall_ms"] / 1000 for r in timed]
    step_lat = {
        name: [
            r["steps"][name]["latency_ms"] / 1000
            for r in timed
            if (r["steps"].get(name) or {}).get("latency_ms")
            and (r["steps"][name].get("tokens_in") or 0) > 0
        ]
        for name in MODEL_STEPS
    }
    tok = [tokens(r) for r in first]
    model_rows = [t for t in tok if t[0] > 0]
    total_in, total_out = sum(t[0] for t in tok), sum(t[1] for t in tok)
    cost = round(total_in / 1e6 * usd[0] + total_out / 1e6 * usd[1], 4) if usd else None

    # Consistency over repeats: same route in every repeat.
    by_case: dict[str, list[str | None]] = collections.defaultdict(list)
    for r in rows:
        by_case[r["case"]].append(r["route"])
    multi = {k: v for k, v in by_case.items() if len(v) > 1}
    consistent = sum(1 for v in multi.values() if len(set(v)) == 1)

    return {
        "cases": n,
        "route_accuracy": pct(correct, n),
        "route_correct": correct,
        "route_ci95": wilson(correct, n),
        "right": sorted(r["case"] for r in first if r["route"] == exp[r["case"]]["route"]),
        "latency_cases": len(timed),
        "latency_excluded_sleep": [r["case"] for r in first if sum(tokens(r)) > 0 and slept(r)],
        "unsafe_auto_approvals": unsafe,
        "missed_automations": missed,
        "automatic_denials": auto_denials,
        "escalation_rate": pct(sum(r["route"] == "reviewer" for r in first), n),
        "automation_rate": pct(sum(r["route"] == "auto_approved" for r in first), n),
        "needs_person": {
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "f1": round(f1, 3) if f1 is not None else None,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        },
        "proposal_acceptable": pct(proposal_ok, len(proposal_rows)),
        "proposal_n": len(proposal_rows),
        "photo_accuracy": pct(photo_ok, len(photo_rows)),
        "photo_n": len(photo_rows),
        "photo_wrong": [
            r["case"]
            for r in photo_rows
            if (r["steps"].get("image") or {}).get("check") != exp[r["case"]]["photo"]
        ],
        "proposal_wrong": [
            r["case"] for r in proposal_rows if r["ai_proposal"] not in exp[r["case"]]["proposal"]
        ],
        "route_wrong": [r["case"] for r in first if r["route"] != exp[r["case"]]["route"]],
        "confusion": confusion,
        "by_category": {k: {"correct": v[0], "n": v[1]} for k, v in sorted(by_cat.items())},
        "latency_s": {
            "p50": percentile(walls, 0.5),
            "p95": percentile(walls, 0.95),
            "max": max(walls) if walls else None,
        },
        "step_latency_s": {
            s: {"p50": percentile(v, 0.5), "p95": percentile(v, 0.95), "n": len(v)}
            for s, v in step_lat.items()
            if v
        },
        "tokens": {
            "in": total_in,
            "out": total_out,
            "model_cases": len(model_rows),
            "per_model_case_mean": round(statistics.mean(a + b for a, b in model_rows))
            if model_rows
            else 0,
        },
        "cost_usd": cost,
        "errors": errors,
        "repeats": {"cases_with_repeats": len(multi), "route_consistent": consistent},
    }


# --- SVG helpers -------------------------------------------------------------------------


def svg(width: int, height: int, body: str, title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'font-family="Helvetica, Arial, sans-serif" role="img" aria-label="{html.escape(title)}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<text x="16" y="24" font-size="15" font-weight="bold" fill="#111827">{html.escape(title)}</text>{body}</svg>'
    )


def bar_chart(
    title: str, series: list[tuple[str, float, str]], unit: str, vmax: float | None = None
) -> str:
    w, left, top, row = 720, 230, 44, 34
    vmax = vmax or max((v for _, v, _ in series), default=1) or 1
    plot = w - left - 70
    body = ""
    for i, (label, value, color) in enumerate(series):
        y = top + i * row
        bw = plot * value / vmax
        body += (
            f'<text x="{left - 10}" y="{y + 20}" font-size="12" text-anchor="end" fill="#374151">{html.escape(label)}</text>'
            f'<rect x="{left}" y="{y + 7}" width="{max(bw, 1):.1f}" height="20" rx="3" fill="{color}"/>'
            f'<text x="{left + bw + 6:.1f}" y="{y + 21}" font-size="12" font-weight="bold" fill="#111827">{value:g}{unit}</text>'
        )
    return svg(w, top + row * len(series) + 16, body, title)


def grouped_bars(
    title: str,
    groups: list[str],
    series: list[tuple[str, list[float], str]],
    unit: str,
    vmax: float,
) -> str:
    w, left, top = 760, 60, 70
    plot_h, plot_w = 240, w - left - 20
    gw = plot_w / max(len(groups), 1)
    bw = min(34, (gw - 16) / max(len(series), 1))
    body = ""
    for t in range(0, 101, 25):
        y = top + plot_h - plot_h * t / 100
        body += f'<line x1="{left}" x2="{w - 20}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/><text x="{left - 6}" y="{y + 4:.1f}" font-size="10" text-anchor="end" fill="#6b7280">{vmax * t / 100:g}{unit}</text>'
    for gi, g in enumerate(groups):
        gx = left + gi * gw + (gw - bw * len(series)) / 2
        for si, (_, values, color) in enumerate(series):
            v = values[gi]
            h = plot_h * v / vmax if vmax else 0
            x = gx + si * bw
            body += (
                f'<rect x="{x:.1f}" y="{top + plot_h - h:.1f}" width="{bw - 3:.1f}" height="{h:.1f}" rx="2" fill="{color}"/>'
                f'<text x="{x + (bw - 3) / 2:.1f}" y="{top + plot_h - h - 4:.1f}" font-size="10" text-anchor="middle" fill="#111827">{v:g}</text>'
            )
        body += f'<text x="{left + gi * gw + gw / 2:.1f}" y="{top + plot_h + 16}" font-size="11" text-anchor="middle" fill="#374151">{html.escape(g)}</text>'
    lx = left
    for name, _, color in series:
        body += f'<rect x="{lx}" y="38" width="12" height="12" rx="2" fill="{color}"/><text x="{lx + 16}" y="48" font-size="11" fill="#374151">{html.escape(name)}</text>'
        lx += 24 + 7 * len(name)
    return svg(w, top + plot_h + 30, body, title)


def heat_table(
    title: str, rows: list[str], cols: list[str], cells: dict[tuple[str, str], tuple[int, int]]
) -> str:
    left, top, cw, rh = 210, 70, 120, 26
    w = left + cw * len(cols) + 20
    body = "".join(
        f'<text x="{left + i * cw + cw / 2}" y="{top - 10}" font-size="11" text-anchor="middle" font-weight="bold" fill="#374151">{html.escape(c)}</text>'
        for i, c in enumerate(cols)
    )
    for ri, r in enumerate(rows):
        y = top + ri * rh
        body += f'<text x="{left - 10}" y="{y + 17}" font-size="11" text-anchor="end" fill="#374151">{html.escape(r.replace("_", " "))}</text>'
        for ci, c in enumerate(cols):
            ok, n = cells.get((r, c), (0, 0))
            if not n:
                fill, label = "#f3f4f6", "-"
            else:
                share = ok / n
                fill = "#16a34a" if share == 1 else ("#facc15" if share >= 0.5 else "#ef4444")
                label = f"{ok}/{n}"
            body += f'<rect x="{left + ci * cw + 2}" y="{y + 2}" width="{cw - 4}" height="{rh - 4}" rx="3" fill="{fill}" fill-opacity="0.75"/><text x="{left + ci * cw + cw / 2}" y="{y + 17}" font-size="11" text-anchor="middle" fill="#111827">{label}</text>'
    body += '<text x="16" y="48" font-size="11" fill="#6b7280">Cells: routed as labelled / cases in category</text>'
    return svg(w, top + rh * len(rows) + 16, body, title)


def confusion_svg(title: str, conf: dict[str, dict[str, int]]) -> str:
    left, top, c = 170, 80, 96
    body = "".join(
        f'<text x="{left + i * c + c / 2}" y="{top - 10}" font-size="11" text-anchor="middle" font-weight="bold" fill="#374151">{ROUTE_LABEL[a]}</text>'
        for i, a in enumerate(ROUTES)
    )
    body += f'<text x="{left + 1.5 * c}" y="{top - 30}" font-size="11" text-anchor="middle" fill="#6b7280">Actual route</text>'
    vmax = max((v for row in conf.values() for v in row.values()), default=1) or 1
    for ri, e in enumerate(ROUTES):
        y = top + ri * 44
        body += f'<text x="{left - 10}" y="{y + 27}" font-size="11" text-anchor="end" fill="#374151">Expected: {ROUTE_LABEL[e]}</text>'
        for ci, a in enumerate(ROUTES):
            v = conf[e][a]
            diag = e == a
            base = "79,70,229" if diag else "239,68,68"
            alpha = 0.12 + 0.75 * (v / vmax) if v else 0.04
            body += f'<rect x="{left + ci * c + 2}" y="{y + 2}" width="{c - 4}" height="40" rx="4" fill="rgba({base},{alpha:.2f})"/><text x="{left + ci * c + c / 2}" y="{y + 27}" font-size="14" font-weight="bold" text-anchor="middle" fill="#111827">{v}</text>'
    return svg(left + 3 * c + 20, top + 3 * 44 + 16, body, title)


# --- Main -------------------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--usd-in", type=float, help="USD per million input tokens")
    ap.add_argument("--usd-out", type=float, help="USD per million output tokens")
    args = ap.parse_args()
    usd = (
        (args.usd_in, args.usd_out)
        if args.usd_in is not None and args.usd_out is not None
        else None
    )

    cases, results = load()
    variants = [v for v in ORDER if results.get(v)]
    summary = {v: score_variant(cases, results[v], usd) for v in variants}
    meta = {}
    for v in variants:
        p = BENCH / "results" / f"{v}.meta.json"
        meta[v] = json.loads(p.read_text()) if p.exists() else {}
    out: dict[str, Any] = {
        "cases": len(cases),
        "variants": summary,
        "meta": meta,
        "categories": sorted({c["category"] for c in cases.values()}),
        "expected_routes": dict(
            collections.Counter(c["expected"]["route"] for c in cases.values())
        ),
    }
    if "rules" in summary:
        base = set(summary["rules"]["right"])
        for v in variants[1:]:
            other = set(summary[v]["right"])
            only_base, only_other = sorted(base - other), sorted(other - base)
            summary[v]["vs_rules"] = {
                "only_rules_right": only_base,
                "only_this_right": only_other,
                "mcnemar_exact_p": mcnemar_exact(len(only_base), len(only_other)),
            }
    (BENCH / "summary.json").write_text(json.dumps(out, indent=1))

    FIG.mkdir(parents=True, exist_ok=True)
    names = [LABEL[v] for v in variants]
    (FIG / "route_accuracy.svg").write_text(
        bar_chart(
            "Route accuracy (share of cases routed as labelled)",
            [(LABEL[v], summary[v]["route_accuracy"] or 0, COLOR[v]) for v in variants],
            "%",
            100,
        )
    )
    (FIG / "safety_outcomes.svg").write_text(
        grouped_bars(
            "Safety outcomes per variant (count of cases)",
            ["Unsafe auto-approvals", "Missed automations", "Automatic denials", "Pipeline errors"],
            [
                (
                    LABEL[v],
                    [
                        len(summary[v]["unsafe_auto_approvals"]),
                        len(summary[v]["missed_automations"]),
                        summary[v]["automatic_denials"],
                        len(summary[v]["errors"]),
                    ],
                    COLOR[v],
                )
                for v in variants
            ],
            "",
            max(
                4,
                max(
                    (
                        max(
                            len(summary[v]["unsafe_auto_approvals"]),
                            len(summary[v]["missed_automations"]),
                            len(summary[v]["errors"]),
                        )
                        for v in variants
                    ),
                    default=4,
                ),
            ),
        )
    )
    cats = out["categories"]
    cells = {
        (cat, LABEL[v]): (
            summary[v]["by_category"].get(cat, {}).get("correct", 0),
            summary[v]["by_category"].get(cat, {}).get("n", 0),
        )
        for v in variants
        for cat in cats
    }
    (FIG / "category_accuracy.svg").write_text(
        heat_table("Route accuracy by case category", cats, names, cells)
    )
    for v in variants:
        (FIG / f"confusion_{v}.svg").write_text(
            confusion_svg(f"Routes: expected vs actual — {LABEL[v]}", summary[v]["confusion"])
        )
    model_vs = [v for v in variants if v != "rules"]
    model_vs = [v for v in model_vs if any(summary[v]["step_latency_s"].values())]
    if model_vs:
        steps = [s for s in MODEL_STEPS if any(s in summary[v]["step_latency_s"] for v in model_vs)]
        (FIG / "step_latency.svg").write_text(
            grouped_bars(
                "Median time per AI step, including free-tier throttling (s)",
                steps,
                [
                    (
                        LABEL[v],
                        [summary[v]["step_latency_s"].get(s, {}).get("p50") or 0 for s in steps],
                        COLOR[v],
                    )
                    for v in model_vs
                ],
                "s",
                20.0
                * math.ceil(
                    max(
                        (summary[v]["step_latency_s"].get(s, {}).get("p95") or 0)
                        for v in model_vs
                        for s in steps
                    )
                    / 20.0
                ),
            )
        )
        # Tokens per case, by category (first AI variant).
        v0 = model_vs[0]
        per_cat: dict[str, list[int]] = collections.defaultdict(list)
        for r in results[v0]:
            if r["repeat"] == 1:
                per_cat[r["category"]].append(sum(tokens(r)))
        (FIG / "tokens_by_category.svg").write_text(
            bar_chart(
                f"Mean tokens per case by category — {LABEL[v0]}",
                [
                    (c.replace("_", " "), round(statistics.mean(v)), COLOR[v0])
                    for c, v in sorted(per_cat.items(), key=lambda kv: -statistics.mean(kv[1]))
                ],
                "",
            )
        )

    # RESULTS.md
    lines = [
        "# Benchmark results",
        "",
        f"{len(cases)} labelled cases; expected routes: "
        + ", ".join(f"{ROUTE_LABEL[k]} {v}" for k, v in out["expected_routes"].items())
        + ".",
        "",
        "| Metric | " + " | ".join(names) + " |",
        "|---|" + "---|" * len(variants),
    ]

    def row(label: str, fn: Any) -> None:
        lines.append(f"| {label} | " + " | ".join(str(fn(summary[v])) for v in variants) + " |")

    row("Cases scored", lambda s: s["cases"])
    row("Route accuracy", lambda s: f"{s['route_accuracy']}% ({s['route_correct']}/{s['cases']})")
    row("Unsafe auto-approvals", lambda s: len(s["unsafe_auto_approvals"]))
    row("Missed automations", lambda s: len(s["missed_automations"]))
    row("Automatic denials", lambda s: s["automatic_denials"])
    row(
        "Needs-a-person F1 (P / R)",
        lambda s: (
            f"{s['needs_person']['f1']} ({s['needs_person']['precision']} / {s['needs_person']['recall']})"
        ),
    )
    row("Automation rate", lambda s: f"{s['automation_rate']}%")
    row("Escalation rate", lambda s: f"{s['escalation_rate']}%")
    row("AI proposal acceptable", lambda s: f"{s['proposal_acceptable']}% (n={s['proposal_n']})")
    row("Photo verdict accuracy", lambda s: f"{s['photo_accuracy']}% (n={s['photo_n']})")
    row(
        "Route accuracy 95% CI (Wilson)", lambda s: f"{s['route_ci95'][0]} to {s['route_ci95'][1]}%"
    )
    row(
        "Exact McNemar p vs rules",
        lambda s: s["vs_rules"]["mcnemar_exact_p"] if "vs_rules" in s else "n/a",
    )
    row(
        "Latency p50 / p95 (s), incl. free-tier throttling",
        lambda s: (
            f"{s['latency_s']['p50']} / {s['latency_s']['p95']} (n={s['latency_cases']})"
            if s["latency_cases"]
            else "n/a"
        ),
    )
    row("Tokens in / out (total)", lambda s: f"{s['tokens']['in']:,} / {s['tokens']['out']:,}")
    row("Mean tokens per AI case", lambda s: f"{s['tokens']['per_model_case_mean']:,}")
    row("Pipeline errors", lambda s: len(s["errors"]))
    lines += ["", "## Cases routed differently from the label", ""]
    for v in variants:
        lines.append(
            f"- **{LABEL[v]}**: "
            + (", ".join(f"`{c}`" for c in summary[v]["route_wrong"]) or "none")
        )
    (BENCH / "RESULTS.md").write_text("\n".join(lines) + "\n")
    for v in variants:
        s = summary[v]
        print(
            f"{v:<16} n={s['cases']:<3} route_acc={s['route_accuracy']}% unsafe={len(s['unsafe_auto_approvals'])} "
            f"missed={len(s['missed_automations'])} auto_denials={s['automatic_denials']} photo_acc={s['photo_accuracy']}% "
            f"tokens={s['tokens']['in'] + s['tokens']['out']:,} errors={len(s['errors'])}"
        )


if __name__ == "__main__":
    main()
