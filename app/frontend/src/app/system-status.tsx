"use client";

import { useEffect, useState } from "react";

type Check = { label: string; path: string };
type Result = { ok: boolean; detail: string };

const CHECKS: Check[] = [
  { label: "API", path: "/api/healthz" },
  { label: "Database", path: "/api/readyz" },
];

async function runCheck(path: string): Promise<Result> {
  try {
    const res = await fetch(path, { cache: "no-store" });
    const body: unknown = await res.json().catch(() => null);
    const status =
      body && typeof body === "object" && "status" in body ? String(body.status) : res.statusText;
    return { ok: res.ok, detail: status };
  } catch {
    return { ok: false, detail: "unreachable" };
  }
}

export function SystemStatus() {
  const [results, setResults] = useState<Record<string, Result>>({});

  useEffect(() => {
    let cancelled = false;
    Promise.all(CHECKS.map(async (c) => [c.path, await runCheck(c.path)] as const)).then(
      (entries) => {
        if (!cancelled) setResults(Object.fromEntries(entries));
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section aria-labelledby="status-heading" className="card card-pad flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h2 id="status-heading" className="text-sm font-semibold">
          System status
        </h2>
        <p className="subtle text-xs">Live checks against the API and the database.</p>
      </div>
      <ul className="flex flex-wrap gap-2">
        {CHECKS.map((check) => {
          const result = results[check.path];
          const state = result ? (result.ok ? "ok" : "down") : "checking";
          return (
            <li
              key={check.path}
              data-testid={`status-${check.label.toLowerCase()}`}
              data-state={state}
              className={`badge ${state === "ok" ? "badge-success" : state === "down" ? "badge-danger" : "badge-neutral"} px-3 py-1`}
            >
              <span
                aria-hidden
                className={`h-2 w-2 rounded-full ${state === "ok" ? "bg-emerald-500" : state === "down" ? "bg-red-500" : "animate-pulse bg-zinc-400"}`}
              />
              <span>{check.label}</span>
              <span className="font-normal opacity-80">{state === "checking" ? "Checking…" : result?.detail}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
