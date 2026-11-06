"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { DecisionBadge, ReasonBadge, StrengthBadge } from "@/components/review-badges";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui";
import {
  api,
  CATEGORY_LABELS,
  errorMessage,
  formatDateTime,
  formatMoney,
  type QueueItem,
} from "@/lib/api";

type View = "open" | "decided_by_me" | "decided";

const VIEWS: { key: View; label: string }[] = [
  { key: "open", label: "Needs review" },
  { key: "decided_by_me", label: "Decided by me" },
  { key: "decided", label: "Recently decided" },
];

export default function ReviewPage() {
  return <RequireRole roles={["reviewer", "admin"]}>{() => <Queue />}</RequireRole>;
}

function Queue() {
  const [view, setView] = useState<View>("open");
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/review/queue", { params: { query: { view } } })
      .then(({ data, error }) => {
        if (cancelled) return;
        if (data) {
          setItems(data);
          setError(null);
        } else setError(errorMessage(error, "We couldn't load the queue."));
      })
      .catch(() => !cancelled && setError("Can't reach the server. Try again in a moment."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [view, reloadKey]);

  const refresh = useCallback(() => {
    setLoading(true);
    setReloadKey((k) => k + 1);
  }, []);

  function choose(v: View) {
    if (v === view) return;
    setItems(null);
    setLoading(true);
    setView(v);
  }

  const decided = view !== "open";
  const urgent = items?.filter((i) =>
    ["proposed_denial", "unverified_photo", "ambiguous_call", "critic_concern", "pipeline_error"].includes(i.escalation_reason ?? ""),
  ).length;

  return (
    <section className="flex flex-col gap-6">
      <PageHeader
        title={
          <>
            Review queue
            {items && !decided ? <span className="ml-2 text-zinc-400">({items.length})</span> : null}
          </>
        }
        subtitle="Every case is here for a named reason. Open one to see the evidence and decide."
        actions={
          <button type="button" onClick={refresh} disabled={loading} className="btn btn-secondary">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 10a6 6 0 1 1-1.8-4.3M16 4v3.5h-3.5" />
            </svg>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        }
      />

      {view === "open" && items && items.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="card card-pad">
            <p className="eyebrow">Waiting for a person</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{items.length}</p>
          </div>
          <div className="card card-pad">
            <p className="eyebrow">Need close attention</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-600 dark:text-amber-400">{urgent}</p>
          </div>
          <div className="card card-pad">
            <p className="eyebrow">Claimed by you</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{items.filter((i) => i.claimed_by_me).length}</p>
          </div>
        </div>
      ) : null}

      <div role="tablist" aria-label="Queue filter" className="tabs w-fit">
        {VIEWS.map((v) => (
          <button key={v.key} role="tab" type="button" aria-selected={view === v.key} onClick={() => choose(v.key)} className="tab">
            {v.label}
          </button>
        ))}
      </div>

      {error ? <ErrorNotice>{error}</ErrorNotice> : null}
      {items === null && !error ? <LoadingRows rows={4} /> : null}
      {items?.length === 0 ? (
        <EmptyState
          testId="queue-empty"
          title={
            view === "open"
              ? "No cases need a person right now."
              : view === "decided_by_me"
                ? "You haven't approved or denied any returns yet."
                : "No decisions by people yet."
          }
          body={view === "open" ? "New cases appear here as soon as the governance gate sends them to a person." : undefined}
        />
      ) : null}

      {view === "decided_by_me" && items && items.length > 0 ? (
        <div className="flex flex-wrap gap-2 text-sm" data-testid="my-decision-summary">
          <span className="badge badge-neutral px-3 py-1">
            {items.length} decision{items.length === 1 ? "" : "s"}
          </span>
          <span className="badge badge-success px-3 py-1">{items.filter((i) => i.final_decision === "approve").length} approved</span>
          <span className="badge badge-danger px-3 py-1">{items.filter((i) => i.final_decision === "deny").length} denied</span>
        </div>
      ) : null}

      {items && items.length > 0 ? (
        <div className="card overflow-x-auto">
          <table className="table min-w-[760px]">
            <thead>
              <tr>
                <th>Case</th>
                <th>Item</th>
                <th className="text-right">Refund</th>
                <th>AI suggests</th>
                <th>{decided ? "Decision" : "Why here"}</th>
                <th>{decided ? "Decided" : "Evidence"}</th>
                <th>{decided ? "By" : "Waiting since"}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="hover:bg-indigo-50/40 dark:hover:bg-zinc-800/50">
                  <td className="font-semibold">
                    <Link href={`/review/${c.id}`} className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                      R-{c.case_number}
                    </Link>
                  </td>
                  <td>
                    <Link href={`/review/${c.id}`} className="flex flex-col">
                      <span className="font-medium">{c.product_name}</span>
                      <span className="subtle text-xs">{CATEGORY_LABELS[c.product_category]}</span>
                    </Link>
                  </td>
                  <td className="text-right font-medium tabular-nums">{formatMoney(c.refund_amount_cents)}</td>
                  <td><DecisionBadge decision={c.ai_proposal} /></td>
                  <td>
                    {decided ? (
                      <DecisionBadge decision={c.final_decision} final />
                    ) : (
                      <div className="flex flex-col items-start gap-1">
                        <ReasonBadge reason={c.escalation_reason} />
                        {c.claimed_by_name ? (
                          <span className="subtle flex items-center gap-1 text-xs">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                            {c.claimed_by_me ? "You're on it" : `${c.claimed_by_name} is on it`}
                          </span>
                        ) : null}
                      </div>
                    )}
                  </td>
                  <td>
                    {decided ? (
                      <span className="muted">{c.decided_at ? formatDateTime(c.decided_at) : "—"}</span>
                    ) : (
                      <StrengthBadge strength={c.evidence_strength} />
                    )}
                  </td>
                  <td className="muted">{decided ? c.decided_by_name ?? "—" : formatDateTime(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
