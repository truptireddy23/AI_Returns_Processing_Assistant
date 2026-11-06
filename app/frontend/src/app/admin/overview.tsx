"use client";

import { useEffect, useState } from "react";

import {
  api,
  CATEGORY_LABELS,
  ESCALATION_LABELS,
  errorMessage,
  formatDateTime,
  formatMoney,
  OVERRIDE_LABELS,
  type AdminMetrics,
  type AdminSettings,
} from "@/lib/api";

type Days = 7 | 30 | 90;

const pct = (n: number | null | undefined) => (n === null || n === undefined ? "—" : `${Math.round(n * 100)}%`);

function label(map: Record<string, string>, key: string): string {
  return map[key] ?? (key === "none" ? "No reason recorded" : key.replace(/_/g, " "));
}

export function Overview({ onEditSettings }: { onEditSettings: () => void }) {
  const [days, setDays] = useState<Days>(7);
  const [m, setM] = useState<AdminMetrics | null>(null);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.GET("/api/admin/metrics", { params: { query: { days } } }), api.GET("/api/admin/settings")])
      .then(([metrics, s]) => {
        if (cancelled) return;
        if (metrics.data) {
          setM(metrics.data);
          setError(null);
        } else setError(errorMessage(metrics.error, "We couldn't load the dashboard."));
        if (s.data) setSettings(s.data);
      })
      .catch(() => !cancelled && setError("Can't reach the server."));
    return () => {
      cancelled = true;
    };
  }, [days, reloadKey]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="group" aria-label="Time range" className="tabs">
          {([7, 30, 90] as Days[]).map((d) => (
            <button
              key={d}
              type="button"
              aria-pressed={days === d}
              onClick={() => setDays(d)}
              className="tab"
            >
              Last {d} days
            </button>
          ))}
        </div>
        <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="btn btn-secondary">
          Refresh
        </button>
      </div>

      {settings ? <SettingsStrip s={settings} onEdit={onEditSettings} /> : null}
      {error ? <p role="alert" className="notice notice-danger">{error}</p> : null}
      {!m && !error ? <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">{Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton h-28" />)}</div> : null}
      {m ? <Dashboard m={m} /> : null}
    </div>
  );
}

function SettingsStrip({ s, onEdit }: { s: AdminSettings; onEdit: () => void }) {
  return (
    <div className="card flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3.5 text-sm">
      <span>
        Automatic approvals{" "}
        <span className={`badge ml-1 ${s.automation_enabled ? "badge-success" : "badge-neutral"}`}>
          {s.automation_enabled ? "On" : "Off"}
        </span>
      </span>
      <span>Risk below <strong className="tabular-nums">{Number(s.risk_limit).toFixed(2)}</strong></span>
      <span>Person needed above <strong className="tabular-nums">{formatMoney(s.high_value_limit_cents)}</strong></span>
      <span>QA sample <strong className="tabular-nums">{pct(Number(s.qa_sample_rate))}</strong></span>
      <button type="button" onClick={onEdit} className="btn btn-secondary btn-sm ml-auto">Edit settings</button>
    </div>
  );
}

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card relative flex flex-col gap-1 overflow-hidden p-4">
      <span aria-hidden className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-500 to-violet-500 opacity-80" />
      <span className="eyebrow text-[11px]">{label}</span>
      <span className="text-3xl font-semibold tracking-tight tabular-nums">{value}</span>
      {sub ? <span className="hint">{sub}</span> : null}
    </div>
  );
}

/** A single-hue bar for one value out of a whole; the number is always shown beside it. */
function Meter({ value, max, title }: { value: number; max: number; title: string }) {
  const width = max > 0 ? Math.max(2, (value / max) * 100) : 0;
  return (
    <div className="h-2 w-full rounded-full bg-zinc-100 dark:bg-zinc-800" title={title} role="img" aria-label={title}>
      <div className="h-2 rounded-full bg-indigo-600 dark:bg-indigo-400" style={{ width: `${width}%` }} />
    </div>
  );
}

function Panel({ title, children, note }: { title: string; children: React.ReactNode; note?: string }) {
  return (
    <div className="card flex flex-col gap-3 p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {children}
      {note ? <p className="hint">{note}</p> : null}
    </div>
  );
}

function CountTable({ rows, labels, empty }: { rows: { key: string; count: number }[]; labels: Record<string, string>; empty: string }) {
  if (rows.length === 0) return <p className="subtle text-sm">{empty}</p>;
  const total = rows.reduce((n, r) => n + r.count, 0);
  return (
    <table className="w-full text-sm">
      <tbody>
        {rows.map((r) => (
          <tr key={r.key} className="border-t border-zinc-100 first:border-0 dark:border-zinc-800">
            <td className="py-1.5 pr-3">{label(labels, r.key)}</td>
            <td className="w-1/3 py-1.5 pr-3"><Meter value={r.count} max={total} title={`${label(labels, r.key)}: ${r.count} of ${total}`} /></td>
            <td className="py-1.5 text-right tabular-nums">{r.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function RateTable({ rows, labels }: { rows: { key: string; total: number; agreed: number }[]; labels: Record<string, string> }) {
  if (rows.length === 0) return <p className="subtle text-sm">No reviewer decisions on AI proposals yet.</p>;
  return (
    <table className="w-full text-sm">
      <thead className="text-xs text-zinc-500">
        <tr>
          <th className="pb-1 text-left font-normal" />
          <th className="pb-1 text-left font-normal">Agreed</th>
          <th className="pb-1 text-right font-normal">Decisions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const rate = r.agreed / r.total;
          return (
            <tr key={r.key} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className="py-1.5 pr-3">{label(labels, r.key)}</td>
              <td className="w-1/2 py-1.5 pr-3">
                <span className="flex items-center gap-2">
                  <Meter value={r.agreed} max={r.total} title={`${label(labels, r.key)}: agreed on ${r.agreed} of ${r.total}`} />
                  <span className="w-10 text-right tabular-nums">{pct(rate)}</span>
                </span>
              </td>
              <td className="py-1.5 text-right tabular-nums">{r.total}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Dashboard({ m }: { m: AdminMetrics }) {
  const agreement = m.agreement_total ? m.agreement_agreed / m.agreement_total : null;
  const decidedTotal = m.approved_by_people + m.denied_by_people;
  return (
    <div className="flex flex-col gap-6" data-testid="dashboard">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Tile label="Returns started" value={String(m.returns_started)} sub={`since ${formatDateTime(m.since)}`} />
        <Tile label="Auto-approved" value={String(m.auto_approved)} />
        <Tile label="Sent to a person" value={String(m.sent_to_person)} sub={`Escalation rate ${pct(m.escalation_rate)}`} />
        <Tile label="Waiting on customer" value={String(m.waiting_on_customer)} sub="missing evidence" />
        <Tile label="In the queue now" value={String(m.open_now)} sub={m.oldest_open_at ? `oldest ${formatDateTime(m.oldest_open_at)}` : "queue is empty"} />
        <Tile
          label="Reviewer agreed with AI"
          value={pct(agreement)}
          sub={m.agreement_total ? `of last ${m.agreement_total} decisions` : "no decisions yet"}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Why cases go to a person" note="The gate's first named reason for each escalated return in this period.">
          <CountTable rows={m.escalations_by_reason} labels={ESCALATION_LABELS} empty="No escalations in this period." />
        </Panel>
        <Panel title="In the queue now, by reason">
          <CountTable rows={m.open_by_reason} labels={ESCALATION_LABELS} empty="Nothing is waiting for a reviewer." />
        </Panel>
        <Panel title="Agreement by product type" note={`Last ${m.agreement_sample_size} reviewer decisions where the AI proposed approve or deny.`}>
          <RateTable rows={m.agreement_by_category} labels={CATEGORY_LABELS} />
        </Panel>
        <Panel title="Agreement by escalation reason" note="Low agreement shows where the AI should defer more to people.">
          <RateTable rows={m.agreement_by_reason} labels={ESCALATION_LABELS} />
        </Panel>
        <Panel title="Most common overrides">
          <CountTable rows={m.top_overrides} labels={OVERRIDE_LABELS} empty="Reviewers haven't overridden the AI yet." />
        </Panel>
        <Panel title="Decisions by people" note={m.avg_hours_to_decision !== null && m.avg_hours_to_decision !== undefined ? `Average time from return to decision: ${m.avg_hours_to_decision} h.` : undefined}>
          {decidedTotal === 0 ? (
            <p className="subtle text-sm">No decisions by people in this period.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500">
                <tr>
                  <th className="pb-1 text-left font-normal">Reviewer</th>
                  <th className="pb-1 text-right font-normal">Approved</th>
                  <th className="pb-1 text-right font-normal">Denied</th>
                </tr>
              </thead>
              <tbody>
                {m.reviewers.map((r) => (
                  <tr key={r.name} className="border-t border-zinc-100 dark:border-zinc-800">
                    <td className="py-1.5">{r.name}</td>
                    <td className="py-1.5 text-right tabular-nums">{r.approved}</td>
                    <td className="py-1.5 text-right tabular-nums">{r.denied}</td>
                  </tr>
                ))}
                <tr className="border-t border-zinc-300 font-medium dark:border-zinc-700">
                  <td className="py-1.5">Total</td>
                  <td className="py-1.5 text-right tabular-nums">{m.approved_by_people}</td>
                  <td className="py-1.5 text-right tabular-nums">{m.denied_by_people}</td>
                </tr>
              </tbody>
            </table>
          )}
        </Panel>
      </div>
    </div>
  );
}
