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

  const select = "input w-auto";

  return (
    <div className="flex flex-col gap-4">
      <form
        className="card flex flex-wrap items-end gap-3 p-4"
        onSubmit={(e) => {
          e.preventDefault();
          setEntries(null);
          setApplied(filters);
        }}
      >
        <label className="flex flex-col gap-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Who
          <select value={filters.actor} onChange={(e) => setFilters({ ...filters, actor: e.target.value as ActorType | "" })} className={select}>
            <option value="">Anyone</option>
            {(Object.keys(ACTOR_LABELS) as ActorType[]).map((a) => <option key={a} value={a}>{ACTOR_LABELS[a]}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          What
          <select value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })} className={select}>
            {ACTION_FILTERS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Case
          <input value={filters.caseNumber} onChange={(e) => setFilters({ ...filters, caseNumber: e.target.value })} placeholder="R-213" className={`${select} w-28`} />
        </label>
        <button type="submit" className="btn btn-primary">Apply filters</button>
      </form>

      {error ? <p role="alert" className="notice notice-danger">{error}</p> : null}
      {entries === null && !error ? <div className="skeleton h-64" /> : null}
      {entries?.length === 0 ? <p className="card card-pad subtle text-center text-sm">No entries match.</p> : null}

      {entries && entries.length > 0 ? (
        <div className="card overflow-x-auto">
          <table className="table min-w-[760px]" data-testid="audit-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Case</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="align-top hover:bg-zinc-50/60 dark:hover:bg-zinc-800/40">
                  <td className="muted whitespace-nowrap text-xs">{formatDateTime(e.at)}</td>
                  <td>
                    <span className="badge badge-neutral">{ACTOR_LABELS[e.actor_type]}</span>
                    {e.actor_name ? <span className="subtle mt-1 block text-xs">{e.actor_name}</span> : null}
                  </td>
                  <td className="font-medium">{ACTION_LABELS[e.action] ?? e.action}</td>
                  <td>
                    {e.case_number && e.return_id ? (
                      <Link href={`/review/${e.return_id}`} className="link">R-{e.case_number}</Link>
                    ) : "—"}
                  </td>
                  <td className="muted max-w-md text-xs break-words">{summary(e) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {nextBefore !== null ? (
        <button type="button" onClick={more} disabled={loadingMore} className="btn btn-secondary w-fit">
          {loadingMore ? "Loading…" : "Load older entries"}
        </button>
      ) : null}
      <p className="hint">🔒 The audit log is append-only: the database rejects edits and deletions. Customers are shown by role, not by name.</p>
    </div>
  );
}
