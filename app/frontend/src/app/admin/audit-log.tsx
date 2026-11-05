"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ACTION_LABELS, ACTOR_LABELS, api, errorMessage, formatDateTime, type ActorType, type AuditEntry } from "@/lib/api";

const ACTION_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All actions" },
  { value: "review.", label: "Reviewer actions" },
  { value: "gate.", label: "Gate decisions" },
  { value: "return.", label: "Customer return actions" },
  { value: "check.", label: "Data checks" },
  { value: "pipeline.", label: "Pipeline failures" },
  { value: "admin.", label: "Settings changes" },
  { value: "auth.", label: "Sign-ins" },
];

type Filters = { actor: ActorType | ""; action: string; caseNumber: string };

/** Short, readable summary of an entry's details. */
function summary(e: AuditEntry): string {
  const d = e.details as Record<string, unknown>;
  if (e.action === "admin.settings_changed" && d.changes && typeof d.changes === "object") {
    return Object.entries(d.changes as Record<string, [unknown, unknown]>)
      .map(([k, [from, to]]) => `${k.replace(/_/g, " ")}: ${String(from)} → ${String(to)}`)
      .join(" · ");
  }
  const parts = Object.entries(d)
    .filter(([, v]) => v !== null && v !== "" && !(Array.isArray(v) && v.length === 0))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(", ") : typeof v === "object" ? JSON.stringify(v) : String(v)}`);
  return parts.join(" · ");
}

export function AuditLogView() {
  const [filters, setFilters] = useState<Filters>({ actor: "", action: "", caseNumber: "" });
  const [applied, setApplied] = useState<Filters>(filters);
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  function query(f: Filters, beforeId?: number) {
    const n = Number(f.caseNumber.replace(/^R-?/i, ""));
    return {
      actor_type: f.actor || undefined,
      action: f.action || undefined,
      case_number: f.caseNumber.trim() && Number.isInteger(n) && n > 0 ? n : undefined,
      before_id: beforeId,
      limit: 50,
    };
  }

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/admin/audit", { params: { query: query(applied) } })
      .then(({ data, error }) => {
        if (cancelled) return;
        if (data) {
          setEntries(data.entries);
          setNextBefore(data.next_before_id ?? null);
          setError(null);
        } else setError(errorMessage(error, "We couldn't load the audit log."));
      })
      .catch(() => !cancelled && setError("Can't reach the server."));
    return () => {
      cancelled = true;
    };
  }, [applied]);

  async function more() {
    if (nextBefore === null) return;
    setLoadingMore(true);
    try {
      const { data, error } = await api.GET("/api/admin/audit", { params: { query: query(applied, nextBefore) } });
      if (data) {
        setEntries((cur) => [...(cur ?? []), ...data.entries]);
        setNextBefore(data.next_before_id ?? null);
      } else setError(errorMessage(error, "We couldn't load more entries."));
    } finally {
      setLoadingMore(false);
    }
  }

  const select = "rounded-md border border-zinc-300 bg-transparent px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-950";

  return (
    <div className="flex flex-col gap-4">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setEntries(null);
          setApplied(filters);
        }}
      >
        <label className="flex flex-col gap-1 text-xs text-zinc-500">
          Who
          <select value={filters.actor} onChange={(e) => setFilters({ ...filters, actor: e.target.value as ActorType | "" })} className={select}>
            <option value="">Anyone</option>
            {(Object.keys(ACTOR_LABELS) as ActorType[]).map((a) => <option key={a} value={a}>{ACTOR_LABELS[a]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500">
          What
          <select value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })} className={select}>
            {ACTION_FILTERS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500">
          Case
          <input value={filters.caseNumber} onChange={(e) => setFilters({ ...filters, caseNumber: e.target.value })} placeholder="R-213" className={`${select} w-28`} />
        </label>
        <button type="submit" className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">Apply</button>
      </form>

      {error ? <p role="alert" className="text-red-700 dark:text-red-400">{error}</p> : null}
      {entries === null && !error ? <p className="text-zinc-500">Loading…</p> : null}
      {entries?.length === 0 ? <p className="text-zinc-500">No entries match.</p> : null}

      {entries && entries.length > 0 ? (
        <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full min-w-[760px] text-left text-sm" data-testid="audit-table">
            <thead className="bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2 font-medium">Time</th>
                <th className="px-3 py-2 font-medium">Actor</th>
                <th className="px-3 py-2 font-medium">Action</th>
                <th className="px-3 py-2 font-medium">Case</th>
                <th className="px-3 py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-t border-zinc-200 align-top dark:border-zinc-800">
                  <td className="whitespace-nowrap px-3 py-2 text-zinc-600 dark:text-zinc-400">{formatDateTime(e.at)}</td>
                  <td className="px-3 py-2">
                    {ACTOR_LABELS[e.actor_type]}
                    {e.actor_name ? <span className="block text-xs text-zinc-500">{e.actor_name}</span> : null}
                  </td>
                  <td className="px-3 py-2">{ACTION_LABELS[e.action] ?? e.action}</td>
                  <td className="px-3 py-2">
                    {e.case_number && e.return_id ? (
                      <Link href={`/review/${e.return_id}`} className="underline">R-{e.case_number}</Link>
                    ) : "—"}
                  </td>
                  <td className="max-w-md px-3 py-2 text-xs break-words text-zinc-600 dark:text-zinc-400">{summary(e) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {nextBefore !== null ? (
        <button type="button" onClick={more} disabled={loadingMore} className="w-fit rounded-md border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800">
          {loadingMore ? "Loading…" : "Load older entries"}
        </button>
      ) : null}
      <p className="text-xs text-zinc-500">The audit log is append-only: the database rejects edits and deletions. Customers are shown by role, not by name.</p>
    </div>
  );
}
