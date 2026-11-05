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

  if (error && !saved) return <p role="alert" className="text-red-700 dark:text-red-400">{error}</p>;
  if (!saved || !draft) return <p className="text-zinc-500">Loading…</p>;

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

  const input = "w-32 rounded-md border border-zinc-300 bg-transparent px-2 py-1.5 tabular-nums dark:border-zinc-700";

  return (
    <form
      className="flex max-w-2xl flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
      data-testid="settings-form"
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 font-medium">Automatic approvals</legend>
        <div className="flex gap-4 text-sm">
          {[false, true].map((on) => (
            <label key={String(on)} className="flex items-center gap-2">
              <input type="radio" name="automation" checked={draft.automation_enabled === on} onChange={() => set({ automation_enabled: on })} />
              {on ? "On" : "Off"}
            </label>
          ))}
        </div>
        <p className="text-sm text-zinc-500">
          {draft.automation_enabled
            ? "Clear, low-risk cases with verified evidence are approved without a person."
            : "The AI only recommends: every return goes to a reviewer."}
        </p>
      </fieldset>

      <label className="flex flex-col gap-1">
        <span className="font-medium">Risk must be below</span>
        <input inputMode="decimal" value={draft.risk_limit} onChange={(e) => set({ risk_limit: e.target.value })} className={input} aria-invalid={!!issues.risk_limit} />
        <span className="text-sm text-zinc-500">Account-behaviour score from 0 (no concerns) to 1. At or above this, the case goes to a person as &quot;Elevated risk&quot;.</span>
        {issues.risk_limit ? <span className="text-sm text-red-700 dark:text-red-400">{issues.risk_limit}</span> : null}
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-medium">Refunds above this always need a person</span>
        <span className="flex items-center gap-1">
          $<input inputMode="decimal" value={draft.high_value_dollars} onChange={(e) => set({ high_value_dollars: e.target.value })} className={input} aria-invalid={!!issues.high_value_dollars} data-testid="high-value-input" />
        </span>
        <span className="text-sm text-zinc-500">Refunds above this go to a person as &quot;High value&quot;, even when every check is clear.</span>
        {issues.high_value_dollars ? <span className="text-sm text-red-700 dark:text-red-400">{issues.high_value_dollars}</span> : null}
        {abovePolicy ? (
          <span role="note" className="rounded bg-amber-50 p-2 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            ⚠ The written returns policy (P7) says refunds above {formatMoney(policyCents!)} need a manager. With {formatMoney(limitCents)}, refunds between the two could be approved automatically.
          </span>
        ) : null}
      </label>

      <label className="flex flex-col gap-1">
        <span className="font-medium">Quality-check sample of auto-approvals</span>
        <span className="flex items-center gap-1">
          <input inputMode="numeric" value={draft.qa_percent} onChange={(e) => set({ qa_percent: e.target.value })} className={input} aria-invalid={!!issues.qa_percent} />%
        </span>
        <span className="text-sm text-zinc-500">This share of would-be automatic approvals goes to a reviewer anyway, so the AI&apos;s work keeps being checked.</span>
        {issues.qa_percent ? <span className="text-sm text-red-700 dark:text-red-400">{issues.qa_percent}</span> : null}
      </label>

      <div className="flex flex-col gap-1 rounded-md bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
        <p className="font-medium">Fixed rules (no setting changes these)</p>
        <p>🔒 The AI can never deny a return.</p>
        <p>🔒 Unverified photos are never auto-approved.</p>
        <p>🔒 Ambiguous calls always go to a person.</p>
      </div>

      {error ? <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p> : null}
      {notice ? <p role="status" className="text-sm text-green-700 dark:text-green-400">{notice}</p> : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={!dirty || pending || Object.keys(issues).length > 0}
          className="rounded-md bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
        {dirty ? (
          <button type="button" onClick={() => setDraft(toDraft(saved))} className="rounded-md px-3 py-2 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800">
            Discard
          </button>
        ) : null}
        <span className="text-xs text-zinc-500">
          Last changed {formatDateTime(saved.updated_at)}
          {saved.updated_by_name ? ` by ${saved.updated_by_name}` : ""}. Changes apply to returns checked from now on; cases already in the queue keep their reason.
        </span>
      </div>
    </form>
  );
}
