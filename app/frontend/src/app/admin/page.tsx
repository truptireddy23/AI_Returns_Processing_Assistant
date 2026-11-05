"use client";

import { useState } from "react";

import { RequireRole } from "@/components/require-role";

import { AuditLogView } from "./audit-log";
import { Overview } from "./overview";
import { SettingsForm } from "./settings-form";

type Tab = "overview" | "settings" | "audit";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "settings", label: "Automation settings" },
  { key: "audit", label: "Audit log" },
];

export default function AdminPage() {
  return <RequireRole roles={["admin"]}>{() => <Admin />}</RequireRole>;
}

function Admin() {
  const [tab, setTab] = useState<Tab>("overview");
  return (
    <section className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold">Admin</h1>
      <div role="tablist" aria-label="Admin sections" className="flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            type="button"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === t.key
                ? "border-zinc-900 font-medium dark:border-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "overview" ? <Overview onEditSettings={() => setTab("settings")} /> : null}
      {tab === "settings" ? <SettingsForm /> : null}
      {tab === "audit" ? <AuditLogView /> : null}
    </section>
  );
}
