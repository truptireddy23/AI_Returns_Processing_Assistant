"use client";

import Image from "next/image";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ChatThread } from "@/components/chat-thread";
import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import { ErrorNotice, LoadingRows, PageHeader } from "@/components/ui";
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

  if (error) return <ErrorNotice>{error}</ErrorNotice>;
  if (!ret) return offline ? <p className="notice notice-warning">Can&apos;t reach the server. Retrying…</p> : <LoadingRows rows={3} />;

  const step = STEP_OF[ret.status];
  const done = ret.status === "approved" || ret.status === "denied";
  const outcomeTone =
    ret.status === "approved" ? "notice-success" : ret.status === "denied" ? "notice-danger" : "notice-info";
  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <PageHeader
        back={{ href: "/orders", label: "My orders" }}
        title={`Return R-${ret.case_number}`}
        subtitle={`Order #${ret.order_number} · started ${formatDate(ret.created_at)}`}
        actions={<StatusBadge status={ret.status} />}
      />

      <div className="card card-pad flex flex-col gap-4">
        <ol className="grid grid-cols-4" aria-label="Progress" data-testid="progress">
          {STEPS.map((label, i) => {
            const complete = i < step || (done && i === step);
            const current = i === step && !done;
            return (
              <li key={label} aria-current={i === step ? "step" : undefined} className="relative flex flex-col items-center gap-2 text-center">
                {i > 0 ? (
                  <span
                    aria-hidden
                    className={`absolute top-4 right-1/2 h-0.5 w-full -translate-y-1/2 ${i <= step ? "bg-indigo-500" : "bg-zinc-200 dark:bg-zinc-800"}`}
                  />
                ) : null}
                <span
                  className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ring-4 ring-white dark:ring-zinc-900 ${
                    complete
                      ? "bg-indigo-600 text-white"
                      : current
                        ? "bg-white text-indigo-700 ring-indigo-100 outline-2 outline-indigo-600 dark:bg-zinc-900 dark:text-indigo-300"
                        : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800"
                  }`}
                >
                  {complete ? "✓" : i + 1}
                </span>
                <span className={`text-xs ${i === step ? "font-semibold text-zinc-900 dark:text-zinc-100" : "subtle"}`}>{label}</span>
              </li>
            );
          })}
        </ol>
        <div className="flex items-center justify-center gap-2 text-sm" aria-live="polite">
          {offline ? (
            <span className="text-amber-700 dark:text-amber-400">Connection lost. Retrying…</span>
          ) : POLL_WHILE.includes(ret.status) ? (
            <span className="subtle flex items-center gap-2">
              <span className="h-2 w-2 animate-pulse rounded-full bg-sky-500" />
              We&apos;ll update this page automatically.
            </span>
          ) : null}
        </div>
      </div>

      {ret.status === "needs_info" ? (
        <div role="status" className="notice notice-warning flex-col gap-3">
          <p className="font-medium">{ret.customer_message ?? "We need more information to continue."}</p>
          {isOwner && ret.photo_required ? (
            <AddPhoto returnId={ret.id} onSent={(updated) => { setRet(updated); setReload((n) => n + 1); }} />
          ) : null}
        </div>
      ) : ret.customer_message ? (
        <div className={`notice ${outcomeTone}`} data-testid="customer-message">
          <p className="leading-relaxed">{ret.customer_message}</p>
        </div>
      ) : null}

      {isOwner && ret.can_request_review ? (
        <RequestReview returnId={ret.id} onSent={(updated) => setRet(updated)} />
      ) : null}

      <div className="grid gap-6 sm:grid-cols-[1fr_auto]">
        <dl className="card card-pad grid grid-cols-[auto_1fr] items-center gap-x-6 gap-y-3 text-sm">
          <dt className="eyebrow">Item</dt>
          <dd className="flex items-center gap-3">
            {ret.product_photo_url ? (
              <Image src={ret.product_photo_url} alt="" width={40} height={40} unoptimized className="h-10 w-10 rounded-lg border border-zinc-100 bg-white object-contain p-0.5 dark:border-zinc-800" />
            ) : null}
            <span className="font-medium">{ret.product_name}</span>
          </dd>
          <dt className="eyebrow">Reason</dt>
          <dd>{REASON_LABELS[ret.reason]}</dd>
          {ret.reason_text ? (
            <>
              <dt className="eyebrow">Your note</dt>
              <dd className="whitespace-pre-wrap">{ret.reason_text}</dd>
            </>
          ) : null}
          <dt className="eyebrow">Refund</dt>
          <dd className="text-base font-semibold tabular-nums">{formatMoney(ret.refund_amount_cents)}</dd>
        </dl>

        {ret.photos.length > 0 ? (
          <div className="card card-pad flex flex-col gap-2">
            <h2 className="eyebrow">Your photo</h2>
            {ret.photos.map((p) => (
              // Served by the API only to you and our reviewers (needs your session cookie).
              // eslint-disable-next-line @next/next/no-img-element
              <img key={p.id} src={p.url} alt="Photo you uploaded" className="max-h-56 w-fit rounded-lg border border-zinc-200 dark:border-zinc-800" />
            ))}
          </div>
        ) : null}
      </div>

      {isOwner ? (
        <ChatThread
          returnId={ret.id}
          as="customer"
          floating
          context={{ status: ret.status, can_request_review: ret.can_request_review }}
        />
      ) : null}
    </section>
  );
}

/** A denied return can be looked at again once, by a different reviewer (S2). */
function RequestReview({ returnId, onSent }: { returnId: string; onSent: (r: ReturnCase) => void }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function send() {
    setPending(true);
    setError(null);
    try {
      const { data, error } = await api.POST("/api/returns/{return_id}/review-request", {
        params: { path: { return_id: returnId } },
        body: { explanation: text.trim() },
      });
      if (data) onSent(data);
      else setError(errorMessage(error, "We couldn't send your request."));
    } catch {
      setError("Can't reach the server. Please try again.");
    } finally {
      setPending(false);
    }
  }

  if (!open) {
    return (
      <div className="card card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-medium">Think we got it wrong?</p>
          <p className="muted text-sm">A different member of our team will take a fresh look.</p>
        </div>
        <button type="button" onClick={() => setOpen(true)} className="btn btn-secondary">
          Request a review
        </button>
      </div>
    );
  }
  return (
    <div className="card card-pad flex flex-col gap-3 text-sm">
      <label className="field">
        <span className="label">Tell us what we missed</span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          maxLength={1000}
          className="input"
          placeholder="For example: the sole came apart after two weeks of normal use."
        />
      </label>
      <p className="hint">A different member of our team will look at it. You can ask once per return.</p>
      {error ? <ErrorNotice>{error}</ErrorNotice> : null}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={send}
          disabled={pending || text.trim().length < 10}
          className="btn btn-primary"
        >
          {pending ? "Sending…" : "Send request"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="btn btn-ghost">Cancel</button>
      </div>
    </div>
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
      <label className="field">
        <span className="label">Add a photo of the problem</span>
        <input
          type="file"
          accept={ACCEPTED}
          onChange={(e) => choose(e.target.files?.[0])}
          className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-zinc-800 file:shadow-sm"
        />
      </label>
      {error ? <p role="alert" className="error-text">{error}</p> : null}
      <button
        type="button"
        onClick={send}
        disabled={!file || pending}
        className="btn btn-primary w-fit"
      >
        {pending ? "Sending…" : "Send photo"}
      </button>
    </div>
  );
}
