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
    <section aria-labelledby="status-heading" className="flex flex-col gap-3">
      <h2 id="status-heading" className="text-lg font-medium">
        System status
      </h2>
      <ul className="flex flex-col gap-2">
        {CHECKS.map((check) => {
          const result = results[check.path];
          const state = result ? (result.ok ? "ok" : "down") : "checking";
          return (
            <li
              key={check.path}
              data-testid={`status-${check.label.toLowerCase()}`}
              data-state={state}
              className="flex items-center justify-between rounded-md border border-zinc-200 px-4 py-3 dark:border-zinc-800"
            >
              <span>{check.label}</span>
              <span
                className={
                  state === "ok"
                    ? "text-green-700 dark:text-green-400"
                    : state === "down"
                      ? "text-red-700 dark:text-red-400"
                      : "text-zinc-500"
                }
              >
                {state === "checking" ? "Checking…" : result?.detail}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
