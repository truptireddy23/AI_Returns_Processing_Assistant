"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { DecisionBadge, ReasonBadge, StrengthBadge } from "@/components/review-badges";
import { StatusBadge } from "@/components/status-badge";
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

  async function release() {
    const { data, error } = await api.DELETE("/api/review/cases/{return_id}/claim", { params: { path: { return_id: id } } });
    if (data) setCase(data);
    else setNotice(errorMessage(error, "Couldn't release this case."));
  }

  if (error && !c) return <p role="alert" className="text-red-700 dark:text-red-400">{error}</p>;
  if (!c) return <p className="text-zinc-500">Loading…</p>;

  const open = c.status === "under_review" || c.status === "failed";
  const photoCheck = c.checks.find((k) => k.key === "photo");
  const photoUnverified = photoCheck?.state === "warn";

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Link href="/review" className="w-fit text-sm text-zinc-500 hover:underline">← Review queue</Link>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="text-2xl font-semibold">Case R-{c.case_number}</h1>
          <StatusBadge status={c.status} />
        </div>
        <p className="text-zinc-600 dark:text-zinc-400">
          {c.product_name} · {CATEGORY_LABELS[c.product_category]} · <span className="font-medium text-zinc-900 dark:text-zinc-100">{formatMoney(c.refund_amount_cents)}</span>
          {" "}· Order #{c.order_number}
          {c.is_final_sale ? <span className="ml-2 rounded bg-zinc-200 px-1.5 py-0.5 text-xs dark:bg-zinc-800">Final Sale</span> : null}
        </p>
      </div>

      {/* Why the case is here comes first (M2, M4). */}
      {open && c.escalation_reason ? (
        <div role="note" className="flex flex-col gap-1 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100" data-testid="why-here">
          <p className="text-sm font-semibold uppercase tracking-wide">⚠ {ESCALATION_LABELS[c.escalation_reason]}</p>
          <p className="text-sm">{ESCALATION_HINTS[c.escalation_reason]}</p>
          {c.ai.gate_reasons.length > 1 ? (
            <p className="text-xs">
              Also flagged: {c.ai.gate_reasons.filter((r) => r !== c.escalation_reason).map((r) => ESCALATION_LABELS[r]).join(" · ")}
            </p>
          ) : null}
        </div>
      ) : null}
      {open && photoUnverified && c.escalation_reason !== "unverified_photo" ? (
        <div role="note" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-950 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
          ⚠ Photo not verified — check that it shows this product and looks genuine.
        </div>
      ) : null}

      {c.review_request ? <ReviewRequestPanel c={c} /> : null}

      {!open ? <DecidedPanel c={c} /> : <ClaimBar c={c} onClaim={claim} onRelease={release} />}
      {notice ? <p role="alert" className="text-sm text-red-700 dark:text-red-400">{notice}</p> : null}

      <div className="grid gap-5 md:grid-cols-2">
        <div className="flex flex-col gap-5">
          <Recommendation c={c} />
          <Checks checks={c.checks} />
        </div>
        <div className="flex flex-col gap-5">
          <Evidence c={c} />
          <Policy c={c} />
          <History c={c} />
        </div>
      </div>

      {open ? <DecisionPanel c={c} onDecided={(updated) => setCase(updated)} /> : null}

      <Timeline c={c} />
    </section>
  );
}

// --- Panels -----------------------------------------------------------------

function Card({ title, children, aside }: { title: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</h2>
        {aside}
      </div>
      {children}
    </div>
  );
}

function ClaimBar({ c, onClaim, onRelease }: { c: ReviewCase; onClaim: () => void; onRelease: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-zinc-50 px-3 py-2 text-sm dark:bg-zinc-900">
      {c.claimed_by_me ? (
        <>
          <span>You&apos;re working on this case.</span>
          <button type="button" onClick={onRelease} className="rounded px-2 py-1 text-zinc-600 hover:bg-zinc-200 dark:text-zinc-300 dark:hover:bg-zinc-800">
            Release to queue
          </button>
        </>
      ) : c.claimed_by_name ? (
        <span>{c.claimed_by_name} is working on this case.</span>
      ) : c.can_decide ? (
        <>
          <span className="text-zinc-600 dark:text-zinc-400">Nobody is working on this case.</span>
          <button type="button" onClick={onClaim} className="rounded px-2 py-1 hover:bg-zinc-200 dark:hover:bg-zinc-800">Claim</button>
        </>
      ) : (
        <span className="text-zinc-600 dark:text-zinc-400">{c.cannot_decide_reason}</span>
      )}
    </div>
  );
}

function DecidedPanel({ c }: { c: ReviewCase }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-zinc-200 p-4 dark:border-zinc-800" data-testid="decided">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <DecisionBadge decision={c.final_decision} final />
        <span>
          {c.decided_by_type === "auto" ? "Approved automatically" : `by ${c.decided_by_name ?? "a reviewer"}`}
          {c.decided_at ? ` · ${formatDateTime(c.decided_at)}` : ""}
        </span>
      </div>
      {c.customer_message ? (
        <div className="text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Message sent to the customer</p>
          <p className="mt-1 whitespace-pre-wrap">{c.customer_message}</p>
        </div>
      ) : null}
    </div>
  );
}

function ReviewRequestPanel({ c }: { c: ReviewCase }) {
  const rr = c.review_request!;
  return (
    <div className="flex flex-col gap-1 rounded-md border border-violet-300 bg-violet-50 p-3 text-sm text-violet-950 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-100">
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

function Recommendation({ c }: { c: ReviewCase }) {
  const counted = c.checks.filter((k) => k.state !== "info");
  const clear = counted.filter((k) => k.state === "pass").length;
  const fromRules = c.ai.source === "rules";
  return (
    <Card
      title="Recommendation"
      aside={
        <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300" title={fromRules ? "Produced by the rule-based checks" : "Written by the AI"}>
          {fromRules ? "Rules" : "AI"}
        </span>
      }
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-semibold">{c.ai.proposal ? DECISION_LABELS[c.ai.proposal] : "No recommendation"}</span>
        {c.evidence_strength ? (
          <span className="flex items-center gap-1.5 text-sm">
            Evidence <StrengthBadge strength={c.evidence_strength} />
            <span className="text-zinc-500">({clear} of {counted.length} checks clear)</span>
          </span>
        ) : null}
      </div>
      {c.ai.rationale ? <p className="text-sm">{c.ai.rationale}</p> : null}
      {c.ai.uncertain_about.length > 0 ? (
        <div className="text-sm">
          <p className="font-medium">Uncertain about</p>
          <ul className="ml-4 list-disc text-zinc-700 dark:text-zinc-300">
            {c.ai.uncertain_about.map((u) => <li key={u}>{u}</li>)}
          </ul>
        </div>
      ) : null}
      {c.ai.critic_concern ? (
        <p className="text-sm text-amber-800 dark:text-amber-300">Re-check concern: {c.ai.critic_concern}</p>
      ) : null}
      {c.status === "failed" ? (
        <p className="text-sm text-amber-800 dark:text-amber-300">The automatic checks didn&apos;t finish, so some evidence may be missing.</p>
      ) : null}
      <p className="text-xs text-zinc-500">
        {fromRules
          ? "Produced by the rule-based checks; the photo is not checked automatically yet."
          : "A recommendation, not a decision. You make the call."}
        {c.ai.ran_at ? ` Checked ${formatDateTime(c.ai.ran_at)}.` : ""}
      </p>
    </Card>
  );
}

const CHECK_ICON: Record<Check["state"], { icon: string; tone: string; label: string }> = {
  pass: { icon: "✓", tone: "text-green-700 dark:text-green-400", label: "clear" },
  warn: { icon: "⚠", tone: "text-amber-700 dark:text-amber-400", label: "warning" },
  fail: { icon: "✕", tone: "text-red-700 dark:text-red-400", label: "failed" },
  info: { icon: "•", tone: "text-zinc-500", label: "info" },
};

function Checks({ checks }: { checks: Check[] }) {
  return (
    <Card title="Checks">
      {checks.length === 0 ? <p className="text-sm text-zinc-500">No checks have run on this case.</p> : null}
      <ul className="flex flex-col gap-2 text-sm" data-testid="checks">
        {checks.map((k) => {
          const s = CHECK_ICON[k.state];
          return (
            <li key={k.key} className="flex gap-2">
              <span className={`w-4 shrink-0 font-bold ${s.tone}`} aria-label={s.label}>{s.icon}</span>
              <span className="flex flex-col">
                <span className="font-medium">
                  {k.label}
                  {k.clauses.length ? <span className="ml-1 text-xs font-normal text-zinc-500">({k.clauses.join(", ")})</span> : null}
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
          <blockquote className="mt-2 border-l-2 border-zinc-300 pl-2 whitespace-pre-wrap text-zinc-700 dark:border-zinc-700 dark:text-zinc-300">
            “{c.reason_text}”
            <span className="block text-xs text-zinc-500">Customer&apos;s words</span>
          </blockquote>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <figure className="flex flex-col gap-1">
          {c.product_photo_url ? (
            <Image src={c.product_photo_url} alt={`Catalog photo of ${c.product_name}`} width={240} height={240} unoptimized className="aspect-square w-full rounded border border-zinc-200 object-cover dark:border-zinc-800" />
          ) : (
            <div className="flex aspect-square items-center justify-center rounded border border-dashed text-xs text-zinc-500">No catalog photo</div>
          )}
          <figcaption className="text-xs text-zinc-500">Catalog photo</figcaption>
        </figure>
        {c.photos.length === 0 ? (
          <div className="flex aspect-square items-center justify-center rounded border border-dashed border-zinc-300 p-2 text-center text-xs text-zinc-500 dark:border-zinc-700">
            No customer photo
          </div>
        ) : (
          c.photos.map((p, i) => (
            <figure key={p.id} className="flex flex-col gap-1">
              <a href={p.url} target="_blank" rel="noreferrer" title="Open full size">
                {/* Served by the API only to the customer and staff. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.url} alt={`Customer photo ${i + 1}`} className="aspect-square w-full rounded border border-zinc-200 object-cover dark:border-zinc-800" />
              </a>
              <figcaption className="text-xs text-zinc-500">Customer photo{c.photos.length > 1 ? ` ${i + 1}` : ""}</figcaption>
            </figure>
          ))
        )}
      </div>

      {c.photos.map((p, i) => (
        <dl key={p.id} className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded bg-zinc-50 p-2 text-xs dark:bg-zinc-900">
          <dt className="col-span-2 font-semibold text-zinc-600 dark:text-zinc-300">Photo {c.photos.length > 1 ? i + 1 : ""} file details</dt>
          <dt className="text-zinc-500">Camera data</dt>
          <dd>{p.has_exif ? (p.camera ?? "present, no camera named") : "none (screenshots, downloads, and generated images often have none)"}</dd>
          {p.captured_at ? (<><dt className="text-zinc-500">Taken</dt><dd>{p.captured_at}</dd></>) : null}
          {p.software ? (<><dt className="text-zinc-500">Software</dt><dd>{p.software}</dd></>) : null}
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
    <li className={`text-sm ${k.cited ? "" : "text-zinc-500"}`}>
      <span className="font-medium">{k.clause_id}. {k.title}.</span> {k.body}
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
          <button type="button" onClick={() => setAll((v) => !v)} className="text-xs underline">
            {all ? "Show cited only" : "View all"}
          </button>
        ) : null
      }
    >
      {shown.length === 0 ? <p className="text-sm text-zinc-500">No clauses cited.</p> : null}
      <ul className="flex flex-col gap-2">{shown.map((k) => <ClauseText key={k.clause_id} k={k} />)}</ul>
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
      <p className="text-sm">
        Account {years} · {h.past_orders} other order{h.past_orders === 1 ? "" : "s"} · {h.past_returns} other return{h.past_returns === 1 ? "" : "s"}
        {" "}· {h.recent_returns_30d} in the last 30 days ·{" "}
        {h.other_accounts_at_address ? `${h.other_accounts_at_address} other account(s) at this address` : "no linked accounts"}
      </p>
      {h.risk_score !== null && h.risk_score !== undefined ? (
        <details className="text-sm">
          <summary className="cursor-pointer">Risk score {h.risk_score.toFixed(2)} when checked — how it&apos;s made</summary>
          <ul className="mt-2 flex flex-col gap-1">
            {Object.entries(h.risk_factors).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2">
                <span className="text-zinc-600 dark:text-zinc-400">{FACTOR_LABELS[k] ?? k}</span>
                <span className="tabular-nums">+{v.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {h.risk_notes.length ? <ul className="ml-4 mt-2 list-disc text-zinc-600 dark:text-zinc-400">{h.risk_notes.map((n) => <li key={n}>{n}</li>)}</ul> : null}
        </details>
      ) : null}
      <p className="text-xs text-zinc-500">The customer&apos;s name and contact details are hidden so the decision rests on the evidence.</p>
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
      <div className="rounded-md border border-zinc-200 p-4 text-sm text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
        {c.cannot_decide_reason}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-md border-2 border-zinc-900 p-4 dark:border-zinc-100" data-testid="decision-panel">
      <h2 className="text-base font-semibold">Your decision</h2>

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
                className={`rounded-full border px-3 py-1 text-sm ${
                  override === o
                    ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                    : "border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
                }`}
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
              className="rounded-md border border-zinc-300 bg-transparent px-2 py-1.5 text-sm dark:border-zinc-700"
            />
          ) : null}
        </fieldset>
      ) : null}

      <label className="flex flex-col gap-1 text-sm">
        Note to the customer <span className="text-zinc-500">(optional, added to their message)</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={500}
          rows={2}
          className="rounded-md border border-zinc-300 bg-transparent px-2 py-1.5 dark:border-zinc-700"
        />
      </label>

      {error ? <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p> : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={pending}
          onClick={() => submit("approve", c.clauses.filter((k) => k.cited).map((k) => k.clause_id))}
          className="rounded-md bg-green-700 px-4 py-2 font-medium text-white hover:bg-green-800 disabled:opacity-50"
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
          className="rounded-md border border-red-700 px-4 py-2 font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/40"
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCancel}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="deny-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-lg flex-col gap-4 overflow-y-auto rounded-lg bg-white p-5 text-zinc-900 shadow-xl outline-none dark:bg-zinc-900 dark:text-zinc-100"
      >
        <h2 id="deny-title" className="text-lg font-semibold">Deny this return?</h2>
        <p className="text-sm">
          Case R-{c.case_number} · {c.product_name} · {formatMoney(c.refund_amount_cents)}
        </p>
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium">Policy basis <span className="font-normal text-zinc-500">(the customer sees this)</span></legend>
          {c.clauses.map((k) => (
            <label key={k.clause_id} className="flex gap-2 text-sm">
              <input type="checkbox" checked={chosen.includes(k.clause_id)} onChange={() => toggle(k.clause_id)} className="mt-1" />
              <span>
                <span className="font-medium">{k.clause_id} — {k.title}</span>
                <span className="block text-zinc-500">{k.body}</span>
              </span>
            </label>
          ))}
        </fieldset>
        <p className="rounded bg-zinc-100 p-2 text-sm dark:bg-zinc-800">
          {c.review_request
            ? "This is the customer's review request: your decision is final."
            : "The customer will be told this decision was made by a person, and can request a review."}
        </p>
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onCancel} className="rounded-md px-4 py-2 hover:bg-zinc-100 dark:hover:bg-zinc-800">Cancel</button>
          <button
            type="button"
            disabled={pending || chosen.length === 0}
            onClick={() => onConfirm(chosen)}
            className="rounded-md bg-red-700 px-4 py-2 font-medium text-white hover:bg-red-800 disabled:opacity-50"
          >
            {pending ? "Saving…" : "Confirm denial"}
          </button>
        </div>
        {chosen.length === 0 ? <p className="text-right text-xs text-zinc-500">Choose at least one policy rule.</p> : null}
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
    <details className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Case history ({c.timeline.length})
      </summary>
      <ol className="mt-3 flex flex-col gap-2 text-sm">
        {c.timeline.map((e, i) => {
          const extra = detailText(e.action, e.details);
          return (
            <li key={i} className="grid grid-cols-[10rem_1fr] gap-3">
              <span className="text-xs text-zinc-500">{formatDateTime(e.at)}</span>
              <span>
                {ACTION_LABELS[e.action] ?? e.action}
                {e.actor_name ? <span className="text-zinc-500"> · {e.actor_name}</span> : null}
                {extra ? <span className="block text-xs text-zinc-500">{extra}</span> : null}
              </span>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-xs text-zinc-500">From the append-only audit log. Escalation reason now: <ReasonBadge reason={c.escalation_reason} /></p>
    </details>
  );
}
