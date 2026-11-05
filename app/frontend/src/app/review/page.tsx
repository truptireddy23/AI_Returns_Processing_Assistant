"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import {
  api,
  DECISION_LABELS,
  ESCALATION_REASON_LABELS,
  errorMessage,
  formatMoney,
  type QueueItem,
} from "@/lib/api";

export default function ReviewPage() {
  return <RequireRole roles={["reviewer", "admin"]}>{() => <Queue />}</RequireRole>;
}

function Queue() {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/review/queue").then(({ data, error }) => {
      if (data) setItems(data);
      else setError(errorMessage(error));
    });
  }, []);

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Review queue</h1>
      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {items === null && !error ? <p className="text-zinc-500">Loading…</p> : null}
      {items?.length === 0 ? (
        <p data-testid="queue-empty">No cases need a person right now.</p>
      ) : null}
      <ul className="flex flex-col gap-2">
        {items?.map((c) => (
          <li key={c.id}>
            <Link
              href={`/review/${c.id}`}
              className="flex items-center justify-between gap-4 rounded-md border border-zinc-200 p-3 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
            >
              <span className="font-medium">R-{c.case_number}</span>
              <span>{formatMoney(c.refund_amount_cents)}</span>
              <span className="text-zinc-500">
                {c.ai_proposal ? DECISION_LABELS[c.ai_proposal] : "—"}
              </span>
              <span className="text-sm text-zinc-500">
                {c.escalation_reason ? ESCALATION_REASON_LABELS[c.escalation_reason] : "—"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
