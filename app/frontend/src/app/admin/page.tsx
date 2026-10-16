"use client";

import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { api, errorMessage, formatMoney } from "@/lib/api";
import type { components } from "@/lib/api-schema";

type Settings = components["schemas"]["SettingsOut"];

export default function AdminPage() {
  return <RequireRole roles={["admin"]}>{() => <AutomationSettings />}</RequireRole>;
}

function AutomationSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/admin/settings").then(({ data, error }) => {
      if (data) setSettings(data);
      else setError(errorMessage(error));
    });
  }, []);

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Automation settings</h1>
      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {settings ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2" data-testid="settings">
          <dt className="text-zinc-600 dark:text-zinc-400">Automatic approvals</dt>
          <dd>{settings.automation_enabled ? "On" : "Off"}</dd>
          <dt className="text-zinc-600 dark:text-zinc-400">Risk must be below</dt>
          <dd>{settings.risk_limit}</dd>
          <dt className="text-zinc-600 dark:text-zinc-400">Refunds above this always need a person</dt>
          <dd>{formatMoney(settings.high_value_limit_cents)}</dd>
          <dt className="text-zinc-600 dark:text-zinc-400">QA sample of auto-approvals</dt>
          <dd>{Math.round(Number(settings.qa_sample_rate) * 100)}%</dd>
        </dl>
      ) : !error ? (
        <p className="text-zinc-500">Loading…</p>
      ) : null}
    </section>
  );
}
