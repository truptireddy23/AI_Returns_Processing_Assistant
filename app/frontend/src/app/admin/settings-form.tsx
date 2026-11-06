"use client";

import { useEffect, useState } from "react";

import { api, errorMessage, formatDateTime, formatMoney, type AdminSettings } from "@/lib/api";

type Draft = {
  automation_enabled: boolean;
  risk_limit: string; // 0.00-1.00
  high_value_dollars: string;
  qa_percent: string; // 0-100
};

function toDraft(s: AdminSettings): Draft {
  return {
    automation_enabled: s.automation_enabled,
    risk_limit: Number(s.risk_limit).toFixed(2),
    high_value_dollars: (s.high_value_limit_cents / 100).toFixed(2),
    qa_percent: String(Math.round(Number(s.qa_sample_rate) * 100)),
  };
}

/** Field problems, checked before sending; the API checks the same ranges. */
function problems(d: Draft): Partial<Record<keyof Draft, string>> {
  const out: Partial<Record<keyof Draft, string>> = {};
  const risk = Number(d.risk_limit);
  if (d.risk_limit.trim() === "" || Number.isNaN(risk) || risk < 0 || risk > 1) out.risk_limit = "Enter a number from 0.00 to 1.00.";
  const dollars = Number(d.high_value_dollars);
  if (d.high_value_dollars.trim() === "" || Number.isNaN(dollars) || dollars < 1 || dollars > 10000) out.high_value_dollars = "Enter an amount from $1 to $10,000.";
  const qa = Number(d.qa_percent);
  if (d.qa_percent.trim() === "" || !Number.isInteger(qa) || qa < 0 || qa > 100) out.qa_percent = "Enter a whole percentage from 0 to 100.";
  return out;
}

export function SettingsForm() {
  const [saved, setSaved] = useState<AdminSettings | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/api/admin/settings")
      .then(({ data, error }) => {
        if (cancelled) return;
        if (data) {
          setSaved(data);
          setDraft(toDraft(data));
        } else setError(errorMessage(error, "We couldn't load the settings."));
      })
      .catch(() => !cancelled && setError("Can't reach the server."));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error && !saved) return <p role="alert" className="notice notice-danger">{error}</p>;
  if (!saved || !draft) return <div className="skeleton h-96 max-w-3xl" />;

  const issues = problems(draft);
  const dirty = JSON.stringify(draft) !== JSON.stringify(toDraft(saved));
  const limitCents = Math.round(Number(draft.high_value_dollars) * 100);
  const policyCents = saved.policy_high_value_cents;
  const abovePolicy = policyCents !== null && policyCents !== undefined && !issues.high_value_dollars && limitCents > policyCents;

  const set = (patch: Partial<Draft>) => {
    setNotice(null);
    setDraft({ ...draft, ...patch });
  };

  async function save() {
    if (!draft || Object.keys(issues).length) return;
    setPending(true);
    setError(null);
    try {
      const { data, error } = await api.PUT("/api/admin/settings", {
        body: {
          automation_enabled: draft.automation_enabled,
          risk_limit: Number(draft.risk_limit).toFixed(2),
          high_value_limit_cents: limitCents,
          qa_sample_rate: (Number(draft.qa_percent) / 100).toFixed(2),
        },
      });
      if (data) {
        setSaved(data);
        setDraft(toDraft(data));
        setNotice("Saved. Every return checked from now on uses these settings.");
      } else setError(errorMessage(error, "We couldn't save the settings."));
    } catch {
      setError("Can't reach the server. Nothing was saved.");
    } finally {
      setPending(false);
    }
  }

  const input = "input w-36 tabular-nums";

  return (
    <form
      className="flex max-w-3xl flex-col gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
      data-testid="settings-form"
    >
      <fieldset className="card card-pad flex flex-wrap items-center justify-between gap-4">
        <div className="flex max-w-lg flex-col gap-1">
          <legend className="font-semibold">Automatic approvals</legend>
          <p className="muted text-sm">
          {draft.automation_enabled
            ? "Clear, low-risk cases with verified evidence are approved without a person."
            : "The AI only recommends: every return goes to a reviewer."}
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span aria-hidden className={`font-medium ${draft.automation_enabled ? "text-emerald-700 dark:text-emerald-400" : "subtle"}`}>
            {draft.automation_enabled ? "On" : "Off"}
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={draft.automation_enabled}
            aria-label="Automatic approvals"
            onClick={() => set({ automation_enabled: !draft.automation_enabled })}
            className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors ${draft.automation_enabled ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-700"}`}
          >
            <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${draft.automation_enabled ? "translate-x-6" : "translate-x-1"}`} />
          </button>
        </div>
      </fieldset>

      <div className="card divide-y divide-zinc-100 dark:divide-zinc-800">

      <label className="flex flex-col gap-1.5 p-5">
        <span className="font-semibold">Risk must be below</span>
        <input inputMode="decimal" value={draft.risk_limit} onChange={(e) => set({ risk_limit: e.target.value })} className={input} aria-invalid={!!issues.risk_limit} />
        <span className="muted text-sm">Account-behaviour score from 0 (no concerns) to 1. At or above this, the case goes to a person as &quot;Elevated risk&quot;.</span>
        {issues.risk_limit ? <span className="error-text">{issues.risk_limit}</span> : null}
      </label>

      <label className="flex flex-col gap-1.5 p-5">
        <span className="font-semibold">Refunds above this always need a person</span>
        <span className="flex items-center gap-1">
          $<input inputMode="decimal" value={draft.high_value_dollars} onChange={(e) => set({ high_value_dollars: e.target.value })} className={input} aria-invalid={!!issues.high_value_dollars} data-testid="high-value-input" />
        </span>
        <span className="muted text-sm">Refunds above this go to a person as &quot;High value&quot;, even when every check is clear.</span>
        {issues.high_value_dollars ? <span className="error-text">{issues.high_value_dollars}</span> : null}
        {abovePolicy ? (
          <span role="note" className="notice notice-warning mt-1">
            ⚠ The written returns policy (P7) says refunds above {formatMoney(policyCents!)} need a manager. With {formatMoney(limitCents)}, refunds between the two could be approved automatically.
          </span>
        ) : null}
      </label>

      <label className="flex flex-col gap-1.5 p-5">
        <span className="font-semibold">Quality-check sample of auto-approvals</span>
        <span className="flex items-center gap-1">
          <input inputMode="numeric" value={draft.qa_percent} onChange={(e) => set({ qa_percent: e.target.value })} className={input} aria-invalid={!!issues.qa_percent} />%
        </span>
        <span className="muted text-sm">This share of would-be automatic approvals goes to a reviewer anyway, so the AI&apos;s work keeps being checked.</span>
        {issues.qa_percent ? <span className="error-text">{issues.qa_percent}</span> : null}
      </label>

      </div>

      <div className="card card-pad flex flex-col gap-3 text-sm">
        <div>
          <p className="font-semibold">Fixed rules</p>
          <p className="muted">Built into the governance gate. No setting can change these.</p>
        </div>
        <ul className="grid gap-2 sm:grid-cols-3">
          {["The AI can never deny a return.", "Unverified photos are never auto-approved.", "Ambiguous calls always go to a person."].map((rule) => (
            <li key={rule} className="flex items-start gap-2 rounded-lg bg-zinc-50 px-3 py-2.5 dark:bg-zinc-800/50">
              <span aria-hidden>🔒</span>
              <span>{rule}</span>
            </li>
          ))}
        </ul>
      </div>

      {error ? <p role="alert" className="notice notice-danger">{error}</p> : null}
      {notice ? <p role="status" className="notice notice-success">{notice}</p> : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={!dirty || pending || Object.keys(issues).length > 0}
          className="btn btn-primary"
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
        {dirty ? (
          <button type="button" onClick={() => setDraft(toDraft(saved))} className="btn btn-ghost">
            Discard
          </button>
        ) : null}
        <span className="hint">
          Last changed {formatDateTime(saved.updated_at)}
          {saved.updated_by_name ? ` by ${saved.updated_by_name}` : ""}. Changes apply to returns checked from now on; cases already in the queue keep their reason.
        </span>
      </div>
    </form>
  );
}
