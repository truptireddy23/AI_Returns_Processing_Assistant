"use client";

import Image from "next/image";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChatThread } from "@/components/chat-thread";
import { RequireRole } from "@/components/require-role";
import { DecisionBadge, ReasonBadge, StrengthBadge } from "@/components/review-badges";
import { StatusBadge } from "@/components/status-badge";
import { ErrorNotice, LoadingRows, PageHeader } from "@/components/ui";
import {
  ACTION_LABELS,
  api,
  CATEGORY_LABELS,
  DECISION_LABELS,
  ESCALATION_HINTS,
  ESCALATION_LABELS,
  errorMessage,
  formatDate,
  formatDateTime,
  formatMoney,
  OVERRIDE_LABELS,
  REASON_LABELS,
  type OverrideReason,
  type ReviewCase,
} from "@/lib/api";

type Check = ReviewCase["checks"][number];

const RERUN_POLL_MS = 5000;
const RERUN_POLL_LIMIT_MS = 5 * 60 * 1000;
type Clause = ReviewCase["clauses"][number];

export function CaseView() {
  return <RequireRole roles={["reviewer", "admin"]}>{() => <Case />}</RequireRole>;
}

function Case() {
  const { id } = useParams<{ id: string }>();
  const [c, setCase] = useState<ReviewCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const triedClaim = useRef(false);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/review/cases/{return_id}", { params: { path: { return_id: id } } })
      .then(({ data, error }) => {
        if (cancelled) return;
        if (data) {
          setCase(data);
          setError(null);
        } else setError(errorMessage(error, "We couldn't load this case."));
      })
      .catch(() => !cancelled && setError("Can't reach the server. Try again in a moment."));
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Opening an unclaimed case claims it, so another reviewer doesn't pick it up too.
  useEffect(() => {
    if (!c || triedClaim.current) return;
    triedClaim.current = true;
    if (c.can_decide && !c.claimed_by_me && !c.claimed_by_name) {
      api
        .POST("/api/review/cases/{return_id}/claim", { params: { path: { return_id: c.id } } })
        .then(({ data }) => data && setCase(data))
        .catch(() => undefined);
    }
  }, [c]);

  async function claim() {
    const { data, error } = await api.POST("/api/review/cases/{return_id}/claim", { params: { path: { return_id: id } } });
    if (data) setCase(data);
    else setNotice(errorMessage(error, "Couldn't claim this case."));
  }

  async function rerun() {
    const { data, error } = await api.POST("/api/review/cases/{return_id}/rerun", { params: { path: { return_id: id } } });
    if (data) setCase(data);
    else setNotice(errorMessage(error, "Couldn't re-run the AI checks."));
  }

  // While a re-run is queued or running, refresh until its result lands.
  const rerunPending = c?.rerun_pending ?? false;
  useEffect(() => {
    if (!rerunPending) return;
    const started = Date.now();
    const timer = setInterval(() => {
      if (Date.now() - started > RERUN_POLL_LIMIT_MS) {
        clearInterval(timer);
        setNotice("The AI checks are taking longer than usual. Reload the page to see if they finished.");
        return;
      }
      api
        .GET("/api/review/cases/{return_id}", { params: { path: { return_id: id } } })
        .then(({ data }) => data && setCase(data))
        .catch(() => undefined);
    }, RERUN_POLL_MS);
    return () => clearInterval(timer);
  }, [rerunPending, id]);

  async function release() {
    const { data, error } = await api.DELETE("/api/review/cases/{return_id}/claim", { params: { path: { return_id: id } } });
    if (data) setCase(data);
    else setNotice(errorMessage(error, "Couldn't release this case."));
  }

  if (error && !c) return <ErrorNotice>{error}</ErrorNotice>;
  if (!c) return <LoadingRows rows={5} />;

  const open = c.status === "under_review" || c.status === "failed";
  const photoCheck = c.checks.find((k) => k.key === "photo");
  const photoUnverified = photoCheck?.state === "warn";

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-5">
      <PageHeader
        back={{ href: "/review", label: "Review queue" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            Case R-{c.case_number}
            <StatusBadge status={c.status} />
          </span>
        }
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium text-zinc-800 dark:text-zinc-200">{c.product_name}</span>
            <span>· {CATEGORY_LABELS[c.product_category]}</span>
            <span>· Order #{c.order_number}</span>
            {c.is_final_sale ? <span className="badge badge-warning">Final Sale</span> : null}
          </span>
        }
        actions={
          <div className="text-right">
            <p className="eyebrow">Refund</p>
            <p className="text-2xl font-semibold tabular-nums">{formatMoney(c.refund_amount_cents)}</p>
          </div>
        }
      />

      <LiveTrace returnId={id} active={rerunPending} />

      {/* Why the case is here comes first (M2, M4). */}
      {open && c.escalation_reason ? (
        <div role="note" className="notice notice-warning items-start" data-testid="why-here">
          <WarnIcon />
          <div className="flex flex-col gap-1">
          <p className="font-semibold">Why this case is here: {ESCALATION_LABELS[c.escalation_reason]}</p>
          <p>{ESCALATION_HINTS[c.escalation_reason]}</p>
          {c.ai.gate_reasons.length > 1 ? (
            <p className="text-xs">
              Also flagged: {c.ai.gate_reasons.filter((r) => r !== c.escalation_reason).map((r) => ESCALATION_LABELS[r]).join(" · ")}
            </p>
          ) : null}
          </div>
        </div>
      ) : null}
      {open && photoUnverified && c.escalation_reason !== "unverified_photo" ? (
        <div role="note" className="notice notice-danger">
          <WarnIcon />
          <span><span className="font-semibold">Photo not verified.</span> Check that it shows this product and looks genuine.</span>
        </div>
      ) : null}

      {c.review_request ? <ReviewRequestPanel c={c} /> : null}

      {!open ? <DecidedPanel c={c} /> : <ClaimBar c={c} onClaim={claim} onRelease={release} />}
      {notice ? <ErrorNotice>{notice}</ErrorNotice> : null}

      {/* A single column, in the order a reviewer actually works a case: what the
          system thinks, whether its checks passed, the evidence behind them, the
          policy and history that back it up. A two-column grid here left a
          lopsided gap whenever one side's cards ran shorter than the other's. */}
      <div className="flex flex-col gap-5">
        <Recommendation c={c} onRerun={rerun} />
        <Checks checks={c.checks} />
        <Evidence c={c} />
        <Policy c={c} />
        <History c={c} />
      </div>

      <Card title="Chat" aside={<LiveBadge />}>
        <ChatThread returnId={c.id} as="reviewer" bare />
      </Card>

      {open ? <DecisionPanel c={c} onDecided={(updated) => setCase(updated)} /> : null}

      <Timeline c={c} />
    </section>
  );
}

// --- Panels -----------------------------------------------------------------

function WarnIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden className="mt-0.5 h-5 w-5 shrink-0">
      <path fillRule="evenodd" d="M8.5 2.6a1.7 1.7 0 0 1 3 0l6.3 11.3a1.7 1.7 0 0 1-1.5 2.6H3.7a1.7 1.7 0 0 1-1.5-2.6L8.5 2.6ZM10 7a.8.8 0 0 0-.8.8v3.5a.8.8 0 0 0 1.6 0V7.8A.8.8 0 0 0 10 7Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clipRule="evenodd" />
    </svg>
  );
}

/** Re-run the AI checks on a case that is already with a person, e.g. one checked
 * before a model was configured, or after the checks failed. The fresh result
 * replaces this card; the case stays here and is never decided by the re-run. */
function RerunControl({ c, onRerun }: { c: ReviewCase; onRerun: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  if (c.rerun_pending) {
    return (
      <p role="status" className="muted flex items-center gap-2 border-t border-zinc-100 pt-4 text-sm dark:border-zinc-800">
        <span className="h-2 w-2 animate-pulse rounded-full bg-sky-500" />
        Re-running the AI checks… this card updates on its own, usually within a minute.
      </p>
    );
  }
  if (!c.can_rerun) return null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-zinc-100 pt-4 dark:border-zinc-800">
      <p className="hint">
        Result looks stale or incomplete? Run the AI checks again. The case stays with you either way.
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onRerun();
          } finally {
            setBusy(false);
          }
        }}
        className="btn btn-secondary btn-sm"
      >
        {busy ? "Starting…" : "↻ Re-run AI checks"}
      </button>
    </div>
  );
}

function Card({ title, children, aside }: { title: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="card overflow-hidden">
      <div className="card-header">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h2>
        {aside}
      </div>
      <div className="flex flex-col gap-4 p-5">{children}</div>
    </div>
  );
}

/** Signals that a panel's content updates on its own (the chat thread polls every
 * few seconds) — same visual weight as the Recommendation card's AI/Rules badge. */
function LiveBadge() {
  return (
    <span className="badge badge-success">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
      Live
    </span>
  );
}

function ClaimBar({ c, onClaim, onRelease }: { c: ReviewCase; onClaim: () => void; onRelease: () => void }) {
  return (
    <div className="card flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm">
      {c.claimed_by_me ? (
        <>
          <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-indigo-500" />You&apos;re working on this case.</span>
          <button type="button" onClick={onRelease} className="btn btn-ghost btn-sm">
            Release to queue
          </button>
        </>
      ) : c.claimed_by_name ? (
        <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-amber-500" />{c.claimed_by_name} is working on this case.</span>
      ) : c.can_decide ? (
        <>
          <span className="text-zinc-600 dark:text-zinc-400">Nobody is working on this case.</span>
          <button type="button" onClick={onClaim} className="btn btn-secondary btn-sm">Claim</button>
        </>
      ) : (
        <span className="text-zinc-600 dark:text-zinc-400">{c.cannot_decide_reason}</span>
      )}
    </div>
  );
}

function DecidedPanel({ c }: { c: ReviewCase }) {
  return (
    <div className="card card-pad flex flex-col gap-3" data-testid="decided">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <DecisionBadge decision={c.final_decision} final />
        <span>
          {c.decided_by_type === "auto" ? "Approved automatically" : `by ${c.decided_by_name ?? "a reviewer"}`}
          {c.decided_at ? ` · ${formatDateTime(c.decided_at)}` : ""}
        </span>
      </div>
      {c.customer_message ? (
        <div className="text-sm">
          <p className="eyebrow">Message sent to the customer</p>
          <p className="mt-1.5 rounded-lg bg-zinc-50 p-3 leading-relaxed whitespace-pre-wrap dark:bg-zinc-800/60">{c.customer_message}</p>
        </div>
      ) : null}
    </div>
  );
}

function ReviewRequestPanel({ c }: { c: ReviewCase }) {
  const rr = c.review_request!;
  return (
    <div className="notice notice-violet flex-col gap-1.5">
      <p className="font-semibold">
        Customer asked for a review · {formatDateTime(rr.created_at)}
        {rr.status === "resolved" ? " · resolved" : ""}
      </p>
      <blockquote className="border-l-2 border-violet-400 pl-2 whitespace-pre-wrap">“{rr.customer_explanation}”</blockquote>
      <p className="text-xs">
        Originally denied by {rr.original_decider_is_me ? "you" : rr.original_decider_name}. A different reviewer must decide.
      </p>
    </div>
  );
}

function Recommendation({ c, onRerun }: { c: ReviewCase; onRerun: () => Promise<void> }) {
  const counted = c.checks.filter((k) => k.state !== "info");
  const clear = counted.filter((k) => k.state === "pass").length;
  const fromRules = c.ai.source === "rules";
  return (
    <Card
      title="Recommendation"
      aside={
        <span className={`badge ${fromRules ? "badge-neutral" : "badge-brand"}`} title={fromRules ? "Produced by the rule-based checks" : "Written by the AI"}>
          {fromRules ? "Rules" : "✦ AI"}
        </span>
      }
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xl font-semibold tracking-tight">{c.ai.proposal ? DECISION_LABELS[c.ai.proposal] : "No recommendation"}</span>
        {c.evidence_strength ? (
          <span className="flex items-center gap-1.5 text-sm">
            Evidence <StrengthBadge strength={c.evidence_strength} />
            <span className="text-zinc-500">({clear} of {counted.length} checks clear)</span>
          </span>
        ) : null}
      </div>
      {c.ai.rationale ? <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">{c.ai.rationale}</p> : null}
      {c.ai.uncertain_about.length > 0 ? (
        <div className="rounded-lg bg-amber-50/70 p-3 text-sm dark:bg-amber-950/30">
          <p className="font-medium text-amber-900 dark:text-amber-200">Uncertain about</p>
          <ul className="ml-4 mt-1 list-disc text-amber-900/90 dark:text-amber-100/90">
            {c.ai.uncertain_about.map((u) => <li key={u}>{u}</li>)}
          </ul>
        </div>
      ) : null}
      {c.ai.critic_concern ? (
        <p className="notice notice-warning">Re-check concern: {c.ai.critic_concern}</p>
      ) : null}
      {c.status === "failed" ? (
        <p className="notice notice-warning">The automatic checks didn&apos;t finish, so some evidence may be missing.</p>
      ) : null}
      <p className="hint">
        {fromRules
          ? "Produced by the rule-based checks; the photo is not checked automatically yet."
          : "A recommendation, not a decision. You make the call."}
        {c.ai.ran_at ? ` Checked ${formatDateTime(c.ai.ran_at)}.` : ""}
      </p>
      <RerunControl c={c} onRerun={onRerun} />
    </Card>
  );
}

const CHECK_ICON: Record<Check["state"], { icon: string; tone: string; label: string }> = {
  pass: { icon: "✓", tone: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300", label: "clear" },
  warn: { icon: "!", tone: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300", label: "warning" },
  fail: { icon: "✕", tone: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300", label: "failed" },
  info: { icon: "i", tone: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400", label: "info" },
};

function Checks({ checks }: { checks: Check[] }) {
  return (
    <Card title="Checks">
      {checks.length === 0 ? <p className="subtle text-sm">No checks have run on this case.</p> : null}
      <ul className="-my-1 flex flex-col divide-y divide-zinc-100 text-sm dark:divide-zinc-800" data-testid="checks">
        {checks.map((k) => {
          const s = CHECK_ICON[k.state];
          return (
            <li key={k.key} className="flex gap-3 py-2.5">
              <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${s.tone}`} aria-label={s.label}>{s.icon}</span>
              <span className="flex flex-col">
                <span className="font-medium">
                  {k.label}
                  {k.clauses.length ? <span className="ml-2 font-mono text-[11px] font-normal text-zinc-500">{k.clauses.join(" · ")}</span> : null}
                </span>
                <span className="text-zinc-600 dark:text-zinc-400">{k.detail}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function Evidence({ c }: { c: ReviewCase }) {
  return (
    <Card title="Evidence">
      <div className="text-sm">
        <p>
          <span className="font-medium">{REASON_LABELS[c.reason]}</span>
          <span className="text-zinc-500">
            {" "}· requested {formatDate(c.created_at)}
            {c.delivered_at ? ` · delivered ${formatDate(c.delivered_at)}` : ""}
            {c.days_since_delivery !== null && c.days_since_delivery !== undefined ? ` (day ${c.days_since_delivery})` : ""}
          </span>
        </p>
        {c.reason_text ? (
          <blockquote className="mt-3 rounded-r-lg border-l-4 border-indigo-300 bg-indigo-50/50 px-3 py-2 whitespace-pre-wrap text-zinc-800 dark:border-indigo-800 dark:bg-indigo-950/30 dark:text-zinc-200">
            “{c.reason_text}”
            <span className="subtle mt-1 block text-xs">Customer&apos;s words</span>
          </blockquote>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <figure className="flex flex-col gap-1.5">
          {c.product_photo_url ? (
            <Image src={c.product_photo_url} alt={`Catalog photo of ${c.product_name}`} width={240} height={240} unoptimized className="aspect-square w-full rounded-xl border border-zinc-200 bg-white object-contain p-2 dark:border-zinc-800" />
          ) : (
            <div className="flex aspect-square items-center justify-center rounded-xl border border-dashed border-zinc-300 text-xs text-zinc-500 dark:border-zinc-700">No catalog photo</div>
          )}
          <figcaption className="eyebrow">Catalog photo</figcaption>
        </figure>
        {c.photos.length === 0 ? (
          <div className="flex aspect-square items-center justify-center rounded-xl border border-dashed border-zinc-300 p-2 text-center text-xs text-zinc-500 dark:border-zinc-700">
            No customer photo
          </div>
        ) : (
          c.photos.map((p, i) => (
            <figure key={p.id} className="flex flex-col gap-1.5">
              <a href={p.url} target="_blank" rel="noreferrer" title="Open full size">
                {/* Served by the API only to the customer and staff. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.url} alt={`Customer photo ${i + 1}`} className="aspect-square w-full rounded-xl border border-zinc-200 object-cover shadow-sm transition hover:opacity-90 dark:border-zinc-800" />
              </a>
              <figcaption className="eyebrow">Customer photo{c.photos.length > 1 ? ` ${i + 1}` : ""} · click to enlarge</figcaption>
            </figure>
          ))
        )}
      </div>

      {c.photos.map((p, i) => (
        <dl key={p.id} className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1.5 rounded-xl border border-zinc-100 bg-zinc-50/70 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-800/40">
          <dt className="eyebrow col-span-2 mb-1">Photo {c.photos.length > 1 ? i + 1 : ""} file details</dt>
          <dt className="text-zinc-500">Camera data</dt>
          <dd>{p.has_exif ? (p.camera ?? "present, no camera named") : "none (screenshots, downloads, and generated images often have none)"}</dd>
          {p.captured_at ? (<><dt className="text-zinc-500">Taken</dt><dd>{p.captured_at}</dd></>) : null}
          {p.software ? (<><dt className="text-zinc-500">Software</dt><dd className="font-medium text-amber-700 dark:text-amber-400">{p.software}</dd></>) : null}
          <dt className="text-zinc-500">Generator hints</dt>
          <dd className={p.has_generator_hints ? "font-medium text-red-700 dark:text-red-400" : ""}>{p.has_generator_hints ? "Found — possibly AI-generated" : "None found"}</dd>
          <dt className="text-zinc-500">Size</dt>
          <dd>{p.width && p.height ? `${p.width}×${p.height} px · ` : ""}{Math.round(p.size_bytes / 1024)} KB</dd>
        </dl>
      ))}
    </Card>
  );
}

function ClauseText({ k }: { k: Clause }) {
  return (
    <li className={`flex gap-3 text-sm ${k.cited ? "" : "text-zinc-500"}`}>
      <span className={`mt-0.5 h-fit shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[11px] font-semibold ${k.cited ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300" : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800"}`}>{k.clause_id}</span>
      <span><span className="font-medium">{k.title}.</span> {k.body}</span>
    </li>
  );
}

function Policy({ c }: { c: ReviewCase }) {
  const [all, setAll] = useState(false);
  const cited = c.clauses.filter((k) => k.cited);
  const shown = all ? c.clauses : cited;
  return (
    <Card
      title={`Policy used${c.policy_version ? ` (version ${c.policy_version})` : ""}`}
      aside={
        c.clauses.length > cited.length ? (
          <button type="button" onClick={() => setAll((v) => !v)} className="link text-xs">
            {all ? "Show cited only" : "View all"}
          </button>
        ) : null
      }
    >
      {shown.length === 0 ? <p className="subtle text-sm">No clauses cited.</p> : null}
      <ul className="flex flex-col gap-2.5">{shown.map((k) => <ClauseText key={k.clause_id} k={k} />)}</ul>
    </Card>
  );
}

const FACTOR_LABELS: Record<string, string> = {
  return_rate: "Return rate",
  recent_returns: "Recent returns",
  new_account: "New account",
  shared_address: "Shared address",
  refund_size: "Refund size",
};

function History({ c }: { c: ReviewCase }) {
  const h = c.history;
  const years = h.account_age_days >= 365 ? `${(h.account_age_days / 365).toFixed(1)} yrs` : `${h.account_age_days} days`;
  return (
    <Card title="Customer history">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          ["Account age", years],
          ["Other orders", String(h.past_orders)],
          ["Other returns", String(h.past_returns)],
          ["Last 30 days", `${h.recent_returns_30d} return${h.recent_returns_30d === 1 ? "" : "s"}`],
          ["Linked accounts", h.other_accounts_at_address ? `${h.other_accounts_at_address} at address` : "None"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg bg-zinc-50 px-3 py-2 dark:bg-zinc-800/50">
            <dt className="eyebrow text-[10px]">{label}</dt>
            <dd className="mt-0.5 font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
      {h.risk_score !== null && h.risk_score !== undefined ? (
        <details className="rounded-lg border border-zinc-100 px-3 py-2 text-sm dark:border-zinc-800">
          <summary className="cursor-pointer font-medium">
            Risk score{" "}
            <span className={`badge ml-1 ${h.risk_score >= 0.3 ? "badge-warning" : "badge-success"}`}>{h.risk_score.toFixed(2)}</span>{" "}
            <span className="subtle font-normal">when checked · how it&apos;s made</span>
          </summary>
          <ul className="mt-3 flex flex-col gap-2">
            {Object.entries(h.risk_factors).map(([k, v]) => (
              <li key={k} className="grid grid-cols-[8rem_1fr_3rem] items-center gap-3">
                <span className="muted">{FACTOR_LABELS[k] ?? k}</span>
                <span className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800">
                  <span className="block h-1.5 rounded-full bg-indigo-500" style={{ width: `${Math.min(100, (v / 0.4) * 100)}%` }} />
                </span>
                <span className="text-right tabular-nums">+{v.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {h.risk_notes.length ? <ul className="ml-4 mt-2 list-disc text-zinc-600 dark:text-zinc-400">{h.risk_notes.map((n) => <li key={n}>{n}</li>)}</ul> : null}
        </details>
      ) : null}
      <p className="hint">🔒 The customer&apos;s name and contact details are hidden so the decision rests on the evidence.</p>
    </Card>
  );
}

// --- Decision ---------------------------------------------------------------

const OVERRIDES = Object.keys(OVERRIDE_LABELS) as OverrideReason[];

function DecisionPanel({ c, onDecided }: { c: ReviewCase; onDecided: (c: ReviewCase) => void }) {
  const [override, setOverride] = useState<OverrideReason | null>(null);
  const [overrideNote, setOverrideNote] = useState("");
  const [note, setNote] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const aiDecides = c.ai.proposal === "approve" || c.ai.proposal === "deny";
  const needsReason = (d: "approve" | "deny") => aiDecides && d !== c.ai.proposal;

  async function submit(decision: "approve" | "deny", clauses: string[] = []) {
    setError(null);
    if (needsReason(decision) && !override) {
      setError(`The AI suggested ${DECISION_LABELS[c.ai.proposal!].toLowerCase()}. Pick why you disagree.`);
      setConfirming(false);
      return;
    }
    if (override === "other" && !overrideNote.trim()) {
      setError("Say briefly why you disagree.");
      setConfirming(false);
      return;
    }
    setPending(true);
    try {
      const { data, error } = await api.POST("/api/review/cases/{return_id}/decision", {
        params: { path: { return_id: c.id } },
        body: {
          decision,
          policy_clauses: clauses,
          override_reason: override,
          override_note: override === "other" ? overrideNote.trim() : "",
          note_to_customer: note.trim(),
          confirm_denial: decision === "deny",
        },
      });
      if (data) {
        setConfirming(false);
        onDecided(data);
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        setError(errorMessage(error, "We couldn't save your decision."));
        setConfirming(false);
      }
    } catch {
      setError("Can't reach the server. Your decision wasn't saved.");
    } finally {
      setPending(false);
    }
  }

  if (!c.can_decide) {
    return (
      <div className="notice notice-info">
        {c.cannot_decide_reason}
      </div>
    );
  }

  return (
    <div className="card flex flex-col gap-5 p-5 ring-2 ring-indigo-500/30 sm:p-6" data-testid="decision-panel">
      <div>
        <h2 className="text-lg font-semibold">Your decision</h2>
        <p className="muted text-sm">The AI recommends; you decide. Denials always need a confirmed policy rule.</p>
      </div>

      {aiDecides ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm">
            Disagree with the AI&apos;s <span className="font-medium">{DECISION_LABELS[c.ai.proposal!].toLowerCase()}</span>? Pick a reason
            <span className="text-zinc-500"> (required if your decision differs)</span>
          </legend>
          <div className="flex flex-wrap gap-2">
            {OVERRIDES.map((o) => (
              <button
                key={o}
                type="button"
                aria-pressed={override === o}
                onClick={() => setOverride(override === o ? null : o)}
                className="chip"
              >
                {OVERRIDE_LABELS[o]}
              </button>
            ))}
          </div>
          {override === "other" ? (
            <input
              value={overrideNote}
              onChange={(e) => setOverrideNote(e.target.value)}
              maxLength={200}
              placeholder="Why do you disagree?"
              className="input"
            />
          ) : null}
        </fieldset>
      ) : null}

      <label className="field">
        <span className="label">Note to the customer <span className="subtle font-normal">(optional, added to their message)</span></span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={500}
          rows={2}
          className="input"
        />
      </label>

      {error ? <ErrorNotice>{error}</ErrorNotice> : null}

      <div className="flex flex-wrap gap-3 border-t border-zinc-100 pt-5 dark:border-zinc-800">
        <button
          type="button"
          disabled={pending}
          onClick={() => submit("approve", c.clauses.filter((k) => k.cited).map((k) => k.clause_id))}
          className="btn btn-success btn-lg min-w-36"
        >
          {pending ? "Saving…" : "Approve"}
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={() => {
            setError(null);
            if (needsReason("deny") && !override) {
              setError(`The AI suggested ${DECISION_LABELS[c.ai.proposal!].toLowerCase()}. Pick why you disagree.`);
              return;
            }
            setConfirming(true);
          }}
          className="btn btn-danger-outline btn-lg min-w-36"
        >
          Deny…
        </button>
      </div>

      {confirming ? <DenyDialog c={c} pending={pending} onCancel={() => setConfirming(false)} onConfirm={(clauses) => submit("deny", clauses)} /> : null}
    </div>
  );
}

function DenyDialog({
  c,
  pending,
  onCancel,
  onConfirm,
}: {
  c: ReviewCase;
  pending: boolean;
  onCancel: () => void;
  onConfirm: (clauses: string[]) => void;
}) {
  // Start from the clauses behind the failed checks; the reviewer can change them.
  const failing = c.checks.filter((k) => k.state === "fail").flatMap((k) => k.clauses);
  const [chosen, setChosen] = useState<string[]>(Array.from(new Set(failing)));
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialogRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const toggle = (id: string) => setChosen((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/60 p-4 backdrop-blur-sm" onClick={onCancel}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="deny-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-lg flex-col gap-4 overflow-y-auto rounded-2xl bg-white p-6 text-zinc-900 shadow-2xl outline-none dark:bg-zinc-900 dark:text-zinc-100"
      >
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-950"><WarnIcon /></span>
          <h2 id="deny-title" className="text-lg font-semibold">Deny this return?</h2>
        </div>
        <p className="muted text-sm">
          Case R-{c.case_number} · {c.product_name} · {formatMoney(c.refund_amount_cents)}
        </p>
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium">Policy basis <span className="font-normal text-zinc-500">(the customer sees this)</span></legend>
          {c.clauses.map((k) => (
            <label key={k.clause_id} className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-2 text-sm transition-colors ${chosen.includes(k.clause_id) ? "border-red-300 bg-red-50/60 dark:border-red-900 dark:bg-red-950/30" : "border-zinc-200 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"}`}>
              <input type="checkbox" checked={chosen.includes(k.clause_id)} onChange={() => toggle(k.clause_id)} className="checkbox mt-0.5 accent-red-600" />
              <span>
                <span className="font-medium">{k.clause_id} — {k.title}</span>
                <span className="subtle block text-xs">{k.body}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <p className="notice notice-info">
          {c.review_request
            ? "This is the customer's review request: your decision is final."
            : "The customer will be told this decision was made by a person, and can request a review."}
        </p>
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onCancel} className="btn btn-secondary">Cancel</button>
          <button
            type="button"
            disabled={pending || chosen.length === 0}
            onClick={() => onConfirm(chosen)}
            className="btn btn-danger"
          >
            {pending ? "Saving…" : "Confirm denial"}
          </button>
        </div>
        {chosen.length === 0 ? <p className="hint text-right">Choose at least one policy rule.</p> : null}
      </div>
    </div>
  );
}

// --- History ----------------------------------------------------------------

function detailText(action: string, d: Record<string, unknown>): string | null {
  if (action.startsWith("gate.") && Array.isArray(d.reasons)) {
    const reasons = (d.reasons as string[]).map((r) => ESCALATION_LABELS[r as keyof typeof ESCALATION_LABELS] ?? r);
    return [reasons.length ? `Reasons: ${reasons.join(", ")}` : null, d.proposal ? `proposal ${d.proposal}` : null, d.evidence_strength ? `evidence ${d.evidence_strength}` : null]
      .filter(Boolean)
      .join(" · ");
  }
  if (action.startsWith("review.") && d.decision) {
    const parts = [`AI proposed ${d.ai_proposal ?? "—"}`];
    if (d.agreed_with_ai === false) parts.push(`override: ${d.override_reason}`);
    if (Array.isArray(d.policy_clauses) && d.policy_clauses.length) parts.push(`clauses ${(d.policy_clauses as string[]).join(", ")}`);
    return parts.join(" · ");
  }
  if (action === "check.missing_evidence" && Array.isArray(d.missing)) return `Missing: ${(d.missing as string[]).join(", ")}`;
  return null;
}

function Timeline({ c }: { c: ReviewCase }) {
  return (
    <details className="card px-5 py-4">
      <summary className="cursor-pointer text-sm font-semibold">
        Case history ({c.timeline.length})
      </summary>
      <ol className="mt-4 flex flex-col gap-0 border-l-2 border-zinc-100 pl-4 text-sm dark:border-zinc-800">
        {c.timeline.map((e, i) => {
          const extra = detailText(e.action, e.details);
          return (
            <li key={i} className="relative grid gap-0.5 pb-4 sm:grid-cols-[11rem_1fr] sm:gap-3">
              <span aria-hidden className="absolute top-1.5 -left-[1.4rem] h-2.5 w-2.5 rounded-full border-2 border-white bg-indigo-500 dark:border-zinc-900" />
              <span className="subtle text-xs">{formatDateTime(e.at)}</span>
              <span>
                {ACTION_LABELS[e.action] ?? e.action}
                {e.actor_name ? <span className="subtle"> · {e.actor_name}</span> : null}
                {extra ? <span className="subtle block text-xs">{extra}</span> : null}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="hint mt-1">From the append-only audit log. Escalation reason now: <ReasonBadge reason={c.escalation_reason} /></p>
    </details>
  );
}


type TraceEvent = {
  run_id: string;
  step: string;
  kind: string;
  data: {
    latency_ms?: number;
    model?: string;
    tokens_in?: number;
    tokens_out?: number;
    cost_usd?: string | null;
    stream_chunks?: number;
    tools?: string[];
  };
};

function LiveTrace({ returnId, active }: { returnId: string; active: boolean }) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [connection, setConnection] = useState("Connecting to trace…");
  useEffect(() => {
    const source = new EventSource(`/api/review/cases/${encodeURIComponent(returnId)}/events`);
    source.onopen = () => setConnection(active ? "Live updates" : "Latest trace");
    source.onmessage = (message) => {
      const event: TraceEvent = JSON.parse(message.data);
      setEvents((previous) => {
        const sameRun = previous.filter((item) => item.run_id === event.run_id);
        return [...sameRun, event].slice(-20);
      });
    };
    source.onerror = () => {
      setConnection(active ? "Reconnecting to trace…" : "Trace loaded");
      if (!active) source.close();
    };
    return () => source.close();
  }, [returnId, active]);
  return (
    <details className="card px-5 py-3" open={active || undefined}>
      <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold">
        Pipeline trace
        <span className={`badge ${active ? "badge-info" : "badge-neutral"}`}>
          {active ? <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-500" /> : null}
          {connection}
        </span>
      </summary>
      <ol className="mt-3 space-y-1.5 font-mono text-xs" aria-label="Pipeline trace" aria-live="polite">
        {events.length === 0 ? <li className="subtle font-sans text-sm">No pipeline events yet.</li> : null}
        {events.map((event, index) => (
          <li key={`${event.run_id}-${index}`} className="rounded-md bg-zinc-50 px-2.5 py-1.5 dark:bg-zinc-800/50">
            <span className="font-semibold text-indigo-700 dark:text-indigo-300">{event.step.replaceAll("_", " ")}</span> <span className="subtle">{event.kind}</span>
            {event.data.latency_ms != null ? ` · ${event.data.latency_ms} ms` : ""}
            {event.data.model ? ` · ${event.data.model}` : ""}
            {event.data.tokens_in != null ? ` · ${event.data.tokens_in} input / ${event.data.tokens_out} output tokens` : ""}
            {event.data.cost_usd != null ? ` · estimated $${event.data.cost_usd}` : ""}
            {event.data.stream_chunks ? ` · ${event.data.stream_chunks} streamed chunks` : ""}
            {event.data.tools?.length ? ` · tools: ${event.data.tools.join(", ")}` : ""}
          </li>
        ))}
      </ol>
    </details>
  );
}
