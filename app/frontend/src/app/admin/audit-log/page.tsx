"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { api, errorMessage, formatDateTime, type AuditLogEntry } from "@/lib/api";

export default function AuditLogPage() {
  return <RequireRole roles={["admin"]}>{() => <AuditLog />}</RequireRole>;
}

function AuditLog() {
  const [rows, setRows] = useState<AuditLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [returnId, setReturnId] = useState("");

  function applyResult({ data, error }: { data?: AuditLogEntry[]; error?: unknown }) {
    if (data) {
      setRows(data);
      setError(null);
    } else {
      setError(errorMessage(error, "We couldn't load the audit log."));
    }
  }

  // For the filter form and Clear button (not an effect, so calling this
  // directly is fine).
  async function load(filter?: string) {
    applyResult(
      await api.GET("/api/admin/audit-log", {
        params: { query: filter ? { return_id: filter } : {} },
      }),
    );
  }

  useEffect(() => {
    api.GET("/api/admin/audit-log", { params: { query: {} } }).then(applyResult);
  }, []);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Audit log</h1>
        <Link href="/admin" className="text-sm underline">
          Automation settings
        </Link>
      </div>

      <form
        className="flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          load(returnId.trim() || undefined);
        }}
      >
        <input
          type="text"
          value={returnId}
          onChange={(e) => setReturnId(e.target.value)}
          placeholder="Filter by return id…"
          className="w-80 rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button type="submit" className="rounded border border-zinc-300 px-2 py-1 text-sm">
          Filter
        </button>
        {returnId ? (
          <button
            type="button"
            onClick={() => {
              setReturnId("");
              load();
            }}
            className="text-sm text-zinc-500 underline"
          >
            Clear
          </button>
        ) : null}
      </form>

      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {rows === null && !error ? <p className="text-zinc-500">Loading…</p> : null}
      {rows?.length === 0 ? <p>No entries.</p> : null}

      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-zinc-200 text-left text-zinc-500 dark:border-zinc-800">
              <th className="py-2 pr-4">Time</th>
              <th className="py-2 pr-4">Actor</th>
              <th className="py-2 pr-4">Action</th>
              <th className="py-2 pr-4">Return</th>
              <th className="py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.id} className="border-b border-zinc-100 align-top dark:border-zinc-900">
                <td className="py-2 pr-4 whitespace-nowrap text-zinc-500">
                  {formatDateTime(r.created_at)}
                </td>
                <td className="py-2 pr-4">{r.actor_type}</td>
                <td className="py-2 pr-4 font-mono text-xs">{r.action}</td>
                <td className="py-2 pr-4">
                  {r.return_id ? (
                    <Link href={`/review/${r.return_id}`} className="underline">
                      {r.return_id.slice(0, 8)}…
                    </Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="py-2 font-mono text-xs break-all text-zinc-500">
                  {Object.keys(r.details).length > 0 ? JSON.stringify(r.details) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
