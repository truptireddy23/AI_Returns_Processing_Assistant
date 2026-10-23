"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import { api, csrfHeaders, errorMessage, formatDate, formatMoney, REASON_LABELS, type ReturnCase, type ReturnStatus } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const STEPS = ["Submitted", "Being checked", "Under review", "Done"] as const;
const STEP_OF: Record<ReturnStatus, number> = {
  submitted: 0,
  needs_info: 1,
  checking: 1,
  under_review: 2,
  failed: 2,
  approved: 3,
  denied: 3,
};
// Keep checking while the pipeline is working on it, backing off so an open
// tab doesn't keep a scale-to-zero database awake.
const POLL_WHILE: ReturnStatus[] = ["submitted", "checking"];
const POLL_START_MS = 1500;
const POLL_MAX_MS = 30_000;

export function ReturnStatusView() {
  return <RequireRole roles={["customer", "reviewer", "admin"]}>{() => <Status />}</RequireRole>;
}

function Status() {
  const { id } = useParams<{ id: string }>();
  const [ret, setRet] = useState<ReturnCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [reload, setReload] = useState(0); // bump to start checking again
  const auth = useAuth();
  const isOwner = auth.status === "signed_in" && auth.user.role === "customer";

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let delay = POLL_START_MS;
    async function load() {
      try {
        const { data, error, response } = await api.GET("/api/returns/{return_id}", {
          params: { path: { return_id: id } },
        });
        if (cancelled) return;
        if (response.status >= 500) throw new Error("server unavailable"); // transient: retry
        if (data) {
          setRet(data);
          setError(null);
          setOffline(false);
          if (POLL_WHILE.includes(data.status)) {
            timer = setTimeout(load, delay);
            delay = Math.min(POLL_MAX_MS, Math.round(delay * 1.5));
          }
        } else {
          setError(errorMessage(error, "We couldn't load this return."));
        }
      } catch {
        // Network blip or the API restarting (5xx): keep what we have and retry.
        if (cancelled) return;
        setOffline(true);
        timer = setTimeout(load, delay);
        delay = Math.min(POLL_MAX_MS, Math.round(delay * 1.5));
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id, reload]);

  if (error) return <p role="alert" className="text-red-700">{error}</p>;
  if (!ret) return <p className="text-zinc-500">{offline ? "Can't reach the server. Retrying…" : "Loading…"}</p>;

  const step = STEP_OF[ret.status];
  return (
    <section className="mx-auto flex w-full max-w-xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Return R-{ret.case_number}</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Order #{ret.order_number} · started {formatDate(ret.created_at)}
        </p>
      </div>

      <ol className="grid grid-cols-4 gap-2 text-xs" aria-label="Progress" data-testid="progress">
        {STEPS.map((label, i) => (
          <li key={label} aria-current={i === step ? "step" : undefined} className="flex flex-col gap-1">
            <span className={`h-1.5 rounded ${i <= step ? "bg-zinc-900 dark:bg-zinc-100" : "bg-zinc-200 dark:bg-zinc-800"}`} />
            <span className={i === step ? "font-semibold" : "text-zinc-500"}>{label}</span>
          </li>
        ))}
      </ol>

      <div className="flex items-center gap-2" aria-live="polite">
        <StatusBadge status={ret.status} />
        {offline ? (
          <span className="text-sm text-amber-700">Connection lost. Retrying…</span>
        ) : POLL_WHILE.includes(ret.status) ? (
          <span className="text-sm text-zinc-500">We&apos;ll update this page automatically.</span>
        ) : null}
      </div>

      {ret.status === "needs_info" ? (
        <div role="status" className="flex flex-col gap-3 rounded bg-amber-50 p-3 text-sm text-amber-900">
          <p>{ret.customer_message ?? "We need more information to continue."}</p>
          {isOwner && ret.photo_required ? (
            <AddPhoto returnId={ret.id} onSent={(updated) => { setRet(updated); setReload((n) => n + 1); }} />
          ) : null}
        </div>
      ) : ret.customer_message ? (
        <p className="rounded border border-zinc-200 p-3 text-sm dark:border-zinc-800">{ret.customer_message}</p>
      ) : null}

      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
        <dt className="text-zinc-500">Item</dt>
        <dd className="flex items-center gap-2">
          {ret.product_photo_url ? <Image src={ret.product_photo_url} alt="" width={32} height={32} unoptimized className="rounded" /> : null}
          {ret.product_name}
        </dd>
        <dt className="text-zinc-500">Reason</dt>
        <dd>{REASON_LABELS[ret.reason]}</dd>
        {ret.reason_text ? (
          <>
            <dt className="text-zinc-500">Your note</dt>
            <dd className="whitespace-pre-wrap">{ret.reason_text}</dd>
          </>
        ) : null}
        <dt className="text-zinc-500">Refund</dt>
        <dd>{formatMoney(ret.refund_amount_cents)}</dd>
      </dl>

      {ret.photos.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-medium">Your photo</h2>
          {ret.photos.map((p) => (
            // Served by the API only to you and our reviewers (needs your session cookie).
            // eslint-disable-next-line @next/next/no-img-element
            <img key={p.id} src={p.url} alt="Photo you uploaded" className="max-h-72 w-fit rounded border border-zinc-200" />
          ))}
        </div>
      ) : null}

      <Link href="/orders" className="text-sm underline">Back to my orders</Link>
    </section>
  );
}

const ACCEPTED = "image/jpeg,image/png,image/webp";
const MAX_PHOTO_MB = 10;

function AddPhoto({ returnId, onSent }: { returnId: string; onSent: (r: ReturnCase) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function choose(f: File | undefined) {
    setError(null);
    if (!f) return setFile(null);
    if (!ACCEPTED.split(",").includes(f.type)) return setError("Please choose a JPEG, PNG, or WebP photo.");
    if (f.size > MAX_PHOTO_MB * 1024 * 1024) return setError(`Photos must be under ${MAX_PHOTO_MB} MB.`);
    setFile(f);
  }

  async function send() {
    if (!file) return;
    const body = new FormData();
    body.set("photo", file);
    setPending(true);
    setError(null);
    try {
      const res = await fetch(`/api/returns/${returnId}/photos`, { method: "POST", body, headers: csrfHeaders() });
      const json: unknown = await res.json().catch(() => null);
      if (!res.ok) throw new Error(errorMessage(json, "We couldn't send your photo."));
      onSent(json as ReturnCase);
    } catch (e) {
      setError(e instanceof Error ? e.message : "We couldn't send your photo.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1">
        Add a photo of the problem
        <input type="file" accept={ACCEPTED} onChange={(e) => choose(e.target.files?.[0])} />
      </label>
      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      <button
        type="button"
        onClick={send}
        disabled={!file || pending}
        className="w-fit rounded-md bg-zinc-900 px-3 py-1.5 text-white disabled:opacity-50"
      >
        {pending ? "Sending…" : "Send photo"}
      </button>
    </div>
  );
}
