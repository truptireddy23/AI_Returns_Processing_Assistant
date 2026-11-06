"use client";

import Link from "next/link";

import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";

import { SystemStatus } from "./system-status";

const ROLES = [
  {
    title: "Customers",
    body: "Shop, start a return with a photo, follow it live, chat with the store, and ask for a second look at any denial.",
    icon: "M3 7h18l-1.5 11.2a2 2 0 0 1-2 1.8H6.5a2 2 0 0 1-2-1.8L3 7Zm5 0V6a4 4 0 0 1 8 0v1",
  },
  {
    title: "Reviewers",
    body: "Work a queue where every case says why it's there. See the AI's checks, the photos, the policy and the history, then decide.",
    icon: "M9 12l2 2 4-4M12 3l7 3v5.5c0 4.3-2.9 7.9-7 9.5-4.1-1.6-7-5.2-7-9.5V6l7-3Z",
  },
  {
    title: "Admins",
    body: "Set the limits automation works within, watch agreement between people and the AI, and trace any decision in the audit log.",
    icon: "M4 19V9m6 10V5m6 14v-7m4 7H2",
  },
];

const STEPS = [
  { n: "1", title: "Data check", body: "Plain code confirms the request is complete before any AI runs." },
  { n: "2", title: "AI checks", body: "Policy, photo authenticity, history, a recommendation, and an independent critic." },
  { n: "3", title: "Governance gate", body: "Only clear, low-risk, verified cases are approved automatically." },
  { n: "4", title: "A person decides", body: "Every denial and every judgment call goes to a named reviewer." },
];

export default function Home() {
  const auth = useAuth();
  return (
    <div className="flex flex-col gap-14">
      <section className="relative overflow-hidden rounded-3xl border border-zinc-200/80 bg-white px-6 py-14 shadow-sm sm:px-12 sm:py-16 dark:border-zinc-800 dark:bg-zinc-900">
        <div aria-hidden className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-indigo-400/20 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full bg-violet-400/20 blur-3xl" />
        <div className="relative flex max-w-2xl flex-col gap-5">
          <span className="badge badge-brand w-fit">Governed AI for e-commerce returns</span>
          <h1 className="text-4xl font-semibold tracking-tight text-zinc-900 sm:text-5xl dark:text-zinc-50">
            Fast on the clear cases. <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">A person on the hard ones.</span>
          </h1>
          <p className="text-lg text-zinc-600 dark:text-zinc-400">
            ReturnGuard&apos;s AI reviews clear-cut returns against the store&apos;s policy, the photo, and the customer&apos;s history.
            A person owns every denial and every judgment call.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            {auth.status === "signed_in" ? (
              <Link href={homeFor(auth.user.role)} className="btn btn-primary btn-lg">
                Continue as {auth.user.display_name} →
              </Link>
            ) : (
              <>
                <Link href="/login" className="btn btn-primary btn-lg">Sign in</Link>
                <Link href="/shop" className="btn btn-secondary btn-lg">Browse the shop</Link>
              </>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3" aria-label="Who it's for">
        {ROLES.map((r) => (
          <div key={r.title} className="card card-pad flex flex-col gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-300">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                <path d={r.icon} />
              </svg>
            </span>
            <h2 className="font-semibold">{r.title}</h2>
            <p className="muted text-sm leading-relaxed">{r.body}</p>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-5" aria-labelledby="how-heading">
        <div>
          <p className="eyebrow">How a return is reviewed</p>
          <h2 id="how-heading" className="mt-1 text-xl font-semibold tracking-tight">Four steps, and the AI never has the last word on a no</h2>
        </div>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.n} className="card card-pad flex flex-col gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-zinc-900 text-xs font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900">
                {s.n}
              </span>
              <h3 className="font-medium">{s.title}</h3>
              <p className="muted text-sm">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <SystemStatus />
    </div>
  );
}
