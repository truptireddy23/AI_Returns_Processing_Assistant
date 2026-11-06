"use client";

import { useState } from "react";

import { RequireRole } from "@/components/require-role";
import { PageHeader } from "@/components/ui";

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
    <section className="flex flex-col gap-6">
      <PageHeader title="Admin" subtitle="Oversee how returns are decided: automation limits, agreement with reviewers, and the full audit trail." />
      <div role="tablist" aria-label="Admin sections" className="tabs w-fit">
        {TABS.map((t) => (
          <button key={t.key} role="tab" type="button" aria-selected={tab === t.key} onClick={() => setTab(t.key)} className="tab">
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
