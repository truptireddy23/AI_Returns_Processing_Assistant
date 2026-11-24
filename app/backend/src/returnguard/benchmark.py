"""CP4 benchmark runner: every labelled case through the real review pipeline.

    python -m returnguard.benchmark --variant rules
    python -m returnguard.benchmark --variant model --max-model-cases 28
    python -m returnguard.benchmark --variant model --repeats 3

Each case is created in a private local database (`returnguard_bench` on the local
Postgres), reviewed by `review_return` with the chosen steps and the real governance
gate, measured, and rolled back, so cases never influence each other (e.g. through
shared-address risk) and nothing touches the shared Neon database. Photos live in a
temporary local folder.

Results are appended to docs/study_materials/benchmark/results/<variant>.jsonl, one
row per (case, repeat). Rows already present are skipped, so a run can be resumed,
e.g. the next day when the provider's daily token quota resets. A rate-limit or quota
error stops the run without writing a row for that case.

Keep the machine awake for a run (macOS: `caffeinate -i ...`): sleep pauses the timers
and inflates step latencies. Some photos aren't in git; see the benchmark README.

Variants:
- rules            RuleSteps only (no model calls): the deterministic baseline.
- model            ModelSteps as deployed (policy tools + streaming on).
- model_no_critic  ModelSteps with the critic step removed (never vetoes).
- model_no_tools   ModelSteps with policy function-calling off (clauses in the prompt).
"""

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from returnguard import db, demo_cases
from returnguard.config import get_settings
from returnguard.models import (
    AgentRun,
    PolicyDoc,
    Product,
    ProductPhoto,
    Return,
    Settings,
)
from returnguard.pipeline.llm import OpenAIClient, model_client
from returnguard.pipeline.model_steps import ModelSteps
from returnguard.pipeline.runner import review_return
from returnguard.pipeline.steps import CriticResult, RuleSteps, Steps
from returnguard.product_photos import prepare
from returnguard.seed import seed
from returnguard.storage import get_storage

REPO = Path(__file__).resolve().parents[4]
BENCH = REPO / "docs" / "study_materials" / "benchmark"
SEED_DIR = REPO / "app" / "seed"
BENCH_DB = "postgresql+asyncpg://returnguard:returnguard@localhost:5432/returnguard_bench"


def isolate() -> None:
    """Point the app at the private benchmark database and local photo storage. Called
    from main(), never on import, so importing this module can't redirect anything.
    The model settings (CHAT_*) still come from app/.env."""
    url = os.environ.get("BENCH_DATABASE_URL", BENCH_DB)
    os.environ.update(
        DATABASE_URL=url,
        DATABASE_URL_UNPOOLED=url,
        AWS_ENDPOINT_URL_S3="",
        LOCAL_STORAGE_DIR=tempfile.mkdtemp(prefix="returnguard-bench-"),
        WORKER_WAKE_URL="",
        RUN_JOBS_INLINE="false",
        ENVIRONMENT="local",
    )
    get_settings.cache_clear()
    get_storage.cache_clear()


VARIANTS = ("rules", "model", "model_no_critic", "model_no_tools")


class NoSample(random.Random):
    """QA sampling never picks a case, so routes are deterministic."""

    def random(self) -> float:
        return 0.999


class NoCriticSteps(ModelSteps):
    """Ablation: the critic step is skipped and never vetoes."""

    async def critic(self, *args: Any, **kwargs: Any) -> CriticResult:
        return CriticResult(veto=False, concern=None, source="ablation:no_critic")


def is_quota_error(exc: BaseException) -> bool:
    """Errors that mean "stop and resume later", not a result for this case:
    rate limits / daily quota, and an invalid or missing API key."""
    name, msg = type(exc).__name__, str(exc).lower()
    return (
        name
        in {"RateLimitError", "AuthenticationError", "PermissionDeniedError", "ProviderStalled"}
        or "429" in msg
        or "rate limit" in msg
        or "401" in msg
        or "invalid api key" in msg
    )


# --- Setup -----------------------------------------------------------------------------


async def ensure_database() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        if not await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
        ):
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin.dispose()

    def migrate() -> None:
        from alembic import command
        from alembic.config import Config

        command.upgrade(Config(str(REPO / "app" / "backend" / "alembic.ini")), "head")

    await asyncio.to_thread(migrate)


async def prepare_fixtures(gate: dict[str, Any]) -> None:
    """Seed data, catalog reference photos, and the benchmark's gate settings."""
    async for session in db.get_session():
        summary = await seed(session, SEED_DIR)
        if not summary.skipped:
            await session.commit()
        storage = get_storage(get_settings().product_photo_bucket)
        for folder in sorted((BENCH / "catalog").iterdir()):
            product = await session.scalar(select(Product).where(Product.sku == folder.name))
            if product is None:
                continue
            for position, path in enumerate(sorted(folder.glob("*.jpg"))):
                prepared = prepare(path.read_bytes())
                key = f"products/{product.sku}/{position}-{prepared.source_sha256[:12]}.jpg"
                await storage.put(key, prepared.data, "image/jpeg")
                existing = await session.scalar(
                    select(ProductPhoto).where(
                        ProductPhoto.product_id == product.id, ProductPhoto.position == position
                    )
                )
                if existing is None:
                    session.add(
                        ProductPhoto(
                            product_id=product.id,
                            position=position,
                            storage_key=key,
                            content_type="image/jpeg",
                            width=prepared.width,
                            height=prepared.height,
                            size_bytes=len(prepared.data),
                            source_sha256=prepared.source_sha256,
                            perceptual_hash=prepared.perceptual_hash,
                        )
                    )
                else:
                    existing.storage_key = key
        settings = await session.get_one(Settings, 1)
        settings.automation_enabled = gate["automation_enabled"]
        settings.risk_limit = gate["risk_limit"]
        settings.high_value_limit_cents = gate["high_value_limit_cents"]
        settings.qa_sample_rate = gate["qa_sample_rate"]
        await session.commit()


# --- Steps per variant -------------------------------------------------------------------


def build_steps(variant: str, session: AsyncSession, policy_doc_id: Any) -> Steps:
    if variant == "rules":
        return RuleSteps()
    settings = get_settings()
    client = model_client(settings)
    if client is None:
        raise SystemExit("No CHAT_API_KEY configured: model variants need a provider.")
    if variant == "model_no_tools":
        client = OpenAIClient.from_settings(
            settings.model_copy(update={"chat_tools_enabled": False})
        )
    cls = NoCriticSteps if variant == "model_no_critic" else ModelSteps
    return cls(
        session,
        embedder=client if client.has_embeddings else None,
        chat=client,
        policy_doc_id=policy_doc_id,
        retrieval_k=settings.policy_retrieval_k,
        storage=get_storage(),
        product_photo_storage=get_storage(settings.product_photo_bucket),
    )


# --- One case -------------------------------------------------------------------------


def _note(out: dict[str, Any]) -> str:
    notes = " ".join(out.get("notes") or [])
    text_ = out.get("reason") or out.get("rationale") or notes or out.get("concern") or ""
    return str(text_)[:400]


async def run_case(case: dict[str, Any], variant: str, repeat: int) -> dict[str, Any]:
    """Create, review, measure, roll back."""
    engine = db.get_engine()
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            run_case_spec = {**case, "email": f"r{repeat}-{variant}-{case['email']}"}
            loaded = await demo_cases.load_case(
                session, SEED_DIR, run_case_spec, now=datetime.now(UTC), photo_dir=BENCH / "photos"
            )
            ret = await session.scalar(
                select(Return).where(Return.case_number == loaded.case_number)
            )
            assert ret is not None
            policy = await session.scalar(select(PolicyDoc).where(PolicyDoc.is_active))
            steps = build_steps(variant, session, policy.id if policy else None)
            started = time.perf_counter()
            error = None
            try:
                await review_return(session, ret.id, steps=steps, rng=NoSample())
            except Exception as exc:  # a crash is recorded; a quota error stops the run
                if is_quota_error(exc):
                    raise
                if type(exc).__name__ in {"APIConnectionError", "APITimeoutError"}:
                    raise TransientError(f"{type(exc).__name__}: {exc}") from exc
                error = f"{type(exc).__name__}: {str(exc)[:300]}"
                traceback.print_exc()
            wall_ms = int((time.perf_counter() - started) * 1000)
            ret = await session.get_one(Return, ret.id, populate_existing=True)
            runs = list(
                await session.scalars(
                    select(AgentRun)
                    .where(AgentRun.return_id == ret.id)
                    .order_by(AgentRun.created_at)
                )
            )
            steps_out: dict[str, Any] = {}
            for r in runs:
                out = r.output or {}
                inner: dict[str, Any] = out["output"] if isinstance(out.get("output"), dict) else {}
                steps_out[r.step] = {
                    "latency_ms": r.latency_ms,
                    "model": r.model or inner.get("model"),
                    "tokens_in": r.tokens_in if r.tokens_in is not None else inner.get("tokens_in"),
                    "tokens_out": r.tokens_out
                    if r.tokens_out is not None
                    else inner.get("tokens_out"),
                    "cost_usd": str(r.cost_usd)
                    if r.cost_usd is not None
                    else inner.get("cost_usd"),
                    "source": out.get("source"),
                    "eligibility": out.get("eligibility"),
                    "check": out.get("check"),
                    "proposal": out.get("proposal"),
                    "ambiguous": out.get("ambiguous"),
                    "veto": out.get("veto"),
                    "reasons": out.get("reasons"),
                    "score": out.get("score"),
                    "tool_calls": inner.get("tool_calls"),
                    "note": _note(out),
                }
            return {
                "case": case["key"],
                "category": case["category"],
                "variant": variant,
                "repeat": repeat,
                "at": datetime.now(UTC).isoformat(),
                "status": ret.status.value,
                "route": ret.route.value if ret.route else None,
                "escalation_reason": ret.escalation_reason.value if ret.escalation_reason else None,
                "ai_proposal": ret.ai_proposal.value if ret.ai_proposal else None,
                "evidence_strength": ret.evidence_strength.value if ret.evidence_strength else None,
                "final_decision": ret.final_decision.value if ret.final_decision else None,
                "decided_by_type": ret.decided_by_type.value if ret.decided_by_type else None,
                "refund_cents": ret.refund_amount_cents,
                "wall_ms": wall_ms,
                "steps": steps_out,
                "error": error,
            }
        finally:
            await session.close()
            await outer.rollback()


CASE_TIMEOUT_S = 240  # note: process timers pause while a laptop sleeps (use caffeinate)


class TransientError(Exception):
    """A network drop to the provider: retry the case, never record it as a result."""


class ProviderStalled(Exception):
    """A case did not finish in time twice: treat like a quota stop (resume later)."""

    def __str__(self) -> str:
        return "rate limit / stalled provider: case timed out twice"


async def run_case_with_timeout(case: dict[str, Any], variant: str, repeat: int) -> dict[str, Any]:
    for attempt in range(2):
        try:
            return await asyncio.wait_for(run_case(case, variant, repeat), CASE_TIMEOUT_S)
        except TimeoutError:
            print(f"  {case['key']}: no reply within {CASE_TIMEOUT_S}s (attempt {attempt + 1})")
        except TransientError as exc:
            print(f"  {case['key']}: {exc} (attempt {attempt + 1}); retrying")
            await asyncio.sleep(10)
    raise ProviderStalled()


# --- Main -------------------------------------------------------------------------------


def git_commit() -> str:
    try:
        cmd = ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"]
        return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603
    except Exception:
        return "unknown"


CHILD_TIMEOUT_S = 600  # hard limit for one case, in its own process
EXIT_STOP = 3  # child: quota, invalid key or stalled provider; resume later


def needs_model(case: dict[str, Any], variant: str) -> bool:
    return variant != "rules" and not (
        case["return"]["photo"] is None and case["expected"]["route"] == "customer"
    )


async def run_child(args: argparse.Namespace, spec: dict[str, Any], out_path: Path) -> int:
    """Child process: review exactly one (case, repeat) and append its row."""
    case = next(c for c in spec["cases"] if c["key"] == args.child_case)
    await ensure_database()
    await prepare_fixtures(spec["gate_settings"])
    try:
        row = await run_case_with_timeout(case, args.variant, args.child_repeat)
    except Exception as exc:
        if is_quota_error(exc):
            print(f"provider quota/rate limit/stall at {case['key']}: {exc}")
            return EXIT_STOP
        raise
    finally:
        await db.dispose_engine()
    with out_path.open("a") as f:
        f.write(json.dumps(row) + "\n")
    err = f" ERROR {row['error'][:60]}" if row["error"] else ""
    print(
        f"{args.variant} r{args.child_repeat} {case['key']:<32} route={row['route']} "
        f"reason={row['escalation_reason']} proposal={row['ai_proposal']}{err}",
        flush=True,
    )
    return 0


async def main_async(args: argparse.Namespace) -> int:
    spec = json.loads((BENCH / "cases.json").read_text())
    out_dir = BENCH / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.variant}.jsonl"
    if args.child_case:
        return await run_child(args, spec, out_path)

    missing = sorted(
        {
            c["return"]["photo"]
            for c in spec["cases"]
            if c["return"]["photo"] and not (BENCH / "photos" / c["return"]["photo"]).exists()
        }
    )
    if missing or not (BENCH / "catalog").is_dir():
        raise SystemExit(
            f"Missing local benchmark photos {missing or 'catalog/'}: run `make benchmark-photos`"
        )
    cases = spec["cases"]
    if args.only:
        cases = [c for c in cases if c["key"] in set(args.only)]
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            row = json.loads(line)
            done.add((row["case"], row["repeat"]))

    await ensure_database()
    await prepare_fixtures(spec["gate_settings"])
    settings = get_settings()
    meta = {
        "variant": args.variant,
        "commit": git_commit(),
        "model": None if args.variant == "rules" else settings.chat_model,
        "tools": settings.chat_tools_enabled and args.variant != "model_no_tools",
        "stream": settings.chat_stream_enabled,
    }
    (out_dir / f"{args.variant}.meta.json").write_text(json.dumps(meta, indent=1))
    await db.dispose_engine()

    model_cases = written = 0
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            if (case["key"], repeat) in done:
                continue
            uses_model = needs_model(case, args.variant)
            if (
                uses_model
                and args.max_model_cases is not None
                and model_cases >= args.max_model_cases
            ):
                print(f"budget reached ({args.max_model_cases} model cases); resume later")
                return 0
            cmd = [
                sys.executable,
                "-m",
                "returnguard.benchmark",
                "--variant",
                args.variant,
                "--child-case",
                case["key"],
                "--child-repeat",
                str(repeat),
            ]
            for attempt in (1, 2):
                try:
                    proc = await asyncio.to_thread(
                        subprocess.run, cmd, timeout=CHILD_TIMEOUT_S, check=False
                    )
                except subprocess.TimeoutExpired:
                    print(
                        f"  {case['key']}: killed after {CHILD_TIMEOUT_S}s (attempt {attempt})",
                        flush=True,
                    )
                    continue
                if proc.returncode == EXIT_STOP:
                    print("stopping: provider quota/stall; resume later")
                    return 0
                if proc.returncode != 0:
                    raise SystemExit(f"case {case['key']} crashed (exit {proc.returncode})")
                break
            else:
                print("stopping: the same case hung twice; resume later")
                return 0
            written += 1
            model_cases += int(uses_model)
    print(f"done: {written} new rows -> {out_path.relative_to(REPO)}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--max-model-cases",
        type=int,
        default=None,
        help="stop after this many cases that call the model (quota budget)",
    )
    parser.add_argument("--only", nargs="*", help="case keys to run")
    parser.add_argument("--child-case", help=argparse.SUPPRESS)
    parser.add_argument("--child-repeat", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()
    isolate()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
