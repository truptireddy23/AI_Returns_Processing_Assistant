"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { api, errorMessage, type SettingsOut } from "@/lib/api";

export default function AdminPage() {
  return <RequireRole roles={["admin"]}>{() => <AutomationSettings />}</RequireRole>;
}

function AutomationSettings() {
  const [settings, setSettings] = useState<SettingsOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Local, editable copies of the number fields; null until settings load.
  const [riskLimit, setRiskLimit] = useState("");
  const [highValueLimit, setHighValueLimit] = useState("");
  const [qaRate, setQaRate] = useState("");

  function load() {
    api.GET("/api/admin/settings").then(({ data, error }) => {
      if (data) {
        setSettings(data);
        setRiskLimit(data.risk_limit);
        setHighValueLimit(String(Math.round(data.high_value_limit_cents / 100)));
        setQaRate(data.qa_sample_rate);
        setError(null);
      } else {
        setError(errorMessage(error));
      }
    });
  }

  useEffect(load, []);

  async function save(changes: Record<string, unknown>) {
    setSaved(false);
    const { data, error } = await api.PATCH("/api/admin/settings", { body: changes });
    if (data) {
      setSettings(data);
      setRiskLimit(data.risk_limit);
      setHighValueLimit(String(Math.round(data.high_value_limit_cents / 100)));
      setQaRate(data.qa_sample_rate);
      setError(null);
      setSaved(true);
    } else {
      setError(errorMessage(error, "We couldn't save that change."));
    }
  }

  if (error && !settings) return <p role="alert" className="text-red-700">{error}</p>;
  if (!settings) return <p className="text-zinc-500">Loading…</p>;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Automation settings</h1>
        <Link href="/admin/audit-log" className="text-sm underline">
          Audit log
        </Link>
      </div>
      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {saved ? <p role="status" className="text-sm text-green-700">Saved.</p> : null}

      <div className="flex flex-col gap-4" data-testid="settings">
        <label className="flex items-center justify-between gap-4 rounded border border-zinc-200 p-3 text-sm dark:border-zinc-800">
          Automatic approvals
          <input
            type="checkbox"
            checked={settings.automation_enabled}
            onChange={(e) => save({ automation_enabled: e.target.checked })}
          />
        </label>

        <NumberField
          label="Risk must be below"
          hint="0.00 – 1.00"
          value={riskLimit}
          onChange={setRiskLimit}
          onSave={() => save({ risk_limit: riskLimit })}
        />
        <NumberField
          label="Refunds above this always need a person"
          hint="dollars"
          value={highValueLimit}
          onChange={setHighValueLimit}
          onSave={() => save({ high_value_limit_cents: Math.round(Number(highValueLimit) * 100) })}
        />
        <NumberField
          label="QA sample of auto-approvals"
          hint="0.00 – 1.00"
          value={qaRate}
          onChange={setQaRate}
          onSave={() => save({ qa_sample_rate: qaRate })}
        />

        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm text-zinc-500">
          <dt>Last updated</dt>
          <dd>{new Date(settings.updated_at).toLocaleString()}</dd>
        </dl>
      </div>
    </section>
  );
}

function NumberField({
  label,
  hint,
  value,
  onChange,
  onSave,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  onSave: () => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 rounded border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <span>
        {label} <span className="text-zinc-500">({hint})</span>
      </span>
      <span className="flex items-center gap-2">
        <input
          type="text"
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-24 rounded border border-zinc-300 px-2 py-1 text-right dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="button"
          onClick={onSave}
          className="rounded bg-zinc-900 px-2 py-1 text-xs text-white hover:opacity-90 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Save
        </button>
      </span>
    </label>
  );
}
