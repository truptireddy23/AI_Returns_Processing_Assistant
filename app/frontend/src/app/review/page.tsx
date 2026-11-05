"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { DecisionBadge, ReasonBadge, StrengthBadge } from "@/components/review-badges";
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

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">
          Review queue{items && !decided ? <span className="text-zinc-500"> ({items.length})</span> : null}
        </h1>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div role="tablist" aria-label="Queue filter" className="flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            role="tab"
            type="button"
            aria-selected={view === v.key}
            onClick={() => choose(v.key)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              view === v.key
                ? "border-zinc-900 font-medium dark:border-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {error ? <p role="alert" className="text-red-700 dark:text-red-400">{error}</p> : null}
      {items === null && !error ? <p className="text-zinc-500">Loading…</p> : null}
      {items?.length === 0 ? (
        <p data-testid="queue-empty" className="text-zinc-600 dark:text-zinc-400">
          {view === "open"
            ? "No cases need a person right now."
            : view === "decided_by_me"
              ? "You haven't approved or denied any returns yet."
              : "No decisions by people yet."}
        </p>
      ) : null}

      {view === "decided_by_me" && items && items.length > 0 ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400" data-testid="my-decision-summary">
          {items.length} decision{items.length === 1 ? "" : "s"} ·{" "}
          {items.filter((i) => i.final_decision === "approve").length} approved ·{" "}
          {items.filter((i) => i.final_decision === "deny").length} denied
        </p>
      ) : null}

      {items && items.length > 0 ? (
        <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2 font-medium">Case</th>
                <th className="px-3 py-2 font-medium">Item</th>
                <th className="px-3 py-2 text-right font-medium">Refund</th>
                <th className="px-3 py-2 font-medium">AI suggests</th>
                <th className="px-3 py-2 font-medium">{decided ? "Decision" : "Why here"}</th>
                <th className="px-3 py-2 font-medium">{decided ? "Decided" : "Evidence"}</th>
                <th className="px-3 py-2 font-medium">{decided ? "By" : "Waiting since"}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-t border-zinc-200 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900">
                  <td className="px-3 py-2 font-medium">
                    <Link href={`/review/${c.id}`} className="underline-offset-2 hover:underline">
                      R-{c.case_number}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/review/${c.id}`} className="flex flex-col">
                      <span>{c.product_name}</span>
                      <span className="text-xs text-zinc-500">{CATEGORY_LABELS[c.product_category]}</span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatMoney(c.refund_amount_cents)}</td>
                  <td className="px-3 py-2"><DecisionBadge decision={c.ai_proposal} /></td>
                  <td className="px-3 py-2">
                    {decided ? (
                      <DecisionBadge decision={c.final_decision} final />
                    ) : (
                      <div className="flex flex-col items-start gap-1">
                        <ReasonBadge reason={c.escalation_reason} />
                        {c.claimed_by_name ? (
                          <span className="text-xs text-zinc-500">
                            {c.claimed_by_me ? "You're on it" : `${c.claimed_by_name} is on it`}
                          </span>
                        ) : null}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {decided ? (
                      c.decided_at ? formatDateTime(c.decided_at) : "—"
                    ) : (
                      <StrengthBadge strength={c.evidence_strength} />
                    )}
                  </td>
                  <td className="px-3 py-2 text-zinc-600 dark:text-zinc-400">
                    {decided ? c.decided_by_name ?? "—" : formatDateTime(c.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
