"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui";
import {
  api,
  csrfHeaders,
  errorMessage,
  formatMoney,
  PHOTO_REASONS,
  REASON_LABELS,
  type Order,
  type OrderItem,
  type ReturnCase,
  type ReturnReason,
} from "@/lib/api";

const MAX_PHOTO_MB = 10;
const ACCEPTED = "image/jpeg,image/png,image/webp";

export function StartReturnForm() {
  return <RequireRole roles={["customer"]}>{() => <Form />}</RequireRole>;
}

function Form() {
  const { itemId } = useParams<{ itemId: string }>();
  const router = useRouter();
  const [found, setFound] = useState<{ order: Order; item: OrderItem } | null | undefined>(undefined);
  const [reason, setReason] = useState<ReturnReason | "">("");
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api.GET("/api/orders").then(({ data }) => {
      for (const order of data ?? []) {
        const item = order.items.find((i) => i.id === itemId);
        if (item) return setFound({ order, item });
      }
      setFound(null);
    });
  }, [itemId]);

  const preview = useMemo(() => (photo ? URL.createObjectURL(photo) : null), [photo]);
  useEffect(() => () => (preview ? URL.revokeObjectURL(preview) : undefined), [preview]);

  const needsPhoto = reason !== "" && PHOTO_REASONS.includes(reason);
  // A missing photo doesn't block submitting: the data check asks for it and
  // review waits until it arrives (missing evidence goes back to the customer).
  const ready = reason !== "" && !pending;

  function onPhoto(file: File | undefined) {
    setError(null);
    if (!file) return setPhoto(null);
    if (!ACCEPTED.split(",").includes(file.type)) {
      setPhoto(null);
      return setError("Please choose a JPEG, PNG, or WebP photo.");
    }
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) {
      setPhoto(null);
      return setError(`Photos must be under ${MAX_PHOTO_MB} MB.`);
    }
    setPhoto(file);
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!found || !ready) return;
    const body = new FormData();
    body.set("order_item_id", found.item.id);
    body.set("reason", reason);
    body.set("reason_text", note);
    if (photo) body.set("photo", photo);
    setPending(true);
    setError(null);
    try {
      // Multipart upload: plain fetch, through the same-origin proxy, with the CSRF token.
      const res = await fetch("/api/returns", { method: "POST", body, headers: csrfHeaders() });
      const json: unknown = await res.json().catch(() => null);
      if (!res.ok) throw new Error(errorMessage(json, "We couldn't start your return."));
      router.push(`/returns/${(json as ReturnCase).id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "We couldn't start your return.");
      setPending(false);
    }
  }

  if (found === undefined) return <LoadingRows rows={3} />;
  if (found === null) {
    return (
      <EmptyState
        title="We couldn't find that item in your orders"
        action={<Link href="/orders" className="btn btn-secondary">Back to my orders</Link>}
      />
    );
  }
  const { order, item } = found;
  if (item.return_id) {
    return (
      <EmptyState
        title="You've already started a return for this item"
        action={<Link href={`/returns/${item.return_id}`} className="btn btn-primary">See its status</Link>}
      />
    );
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-2xl flex-col gap-6" aria-label="Start a return">
      <PageHeader back={{ href: "/orders", label: "My orders" }} title="Return an item" subtitle={`Order #${order.order_number}`} />

      <div className="card card-pad flex items-center gap-4">
        {item.photo_url ? (
          <Image src={item.photo_url} alt="" width={64} height={64} unoptimized className="h-16 w-16 rounded-lg border border-zinc-100 bg-white object-contain p-1 dark:border-zinc-800" />
        ) : null}
        <span className="flex-1 font-medium">{item.product_name}</span>
        <span className="font-semibold tabular-nums">{formatMoney(item.unit_price_cents * item.quantity)}</span>
      </div>
      {item.is_final_sale ? (
        <p className="notice notice-warning">
          This item was Final Sale. Final Sale items can only be returned if they arrived damaged, defective, or were the wrong item.
        </p>
      ) : null}

      <div className="card card-pad flex flex-col gap-5">
        <fieldset className="flex flex-col gap-2">
          <legend className="label mb-2">Why are you returning it?</legend>
          <div className="grid gap-2 sm:grid-cols-2" role="radiogroup">
            {Object.entries(REASON_LABELS).map(([value, label]) => {
              const checked = reason === value;
              return (
                <label
                  key={value}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                    checked
                      ? "border-indigo-500 bg-indigo-50 text-indigo-900 ring-2 ring-indigo-500/20 dark:bg-indigo-950/40 dark:text-indigo-100"
                      : "border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                  }`}
                >
                  <input
                    type="radio"
                    name="reason"
                    value={value}
                    required
                    checked={checked}
                    onChange={() => setReason(value as ReturnReason)}
                    className="accent-indigo-600"
                  />
                  <span className="flex-1">{label}</span>
                  {PHOTO_REASONS.includes(value as ReturnReason) ? <span className="badge badge-neutral">Photo</span> : null}
                </label>
              );
            })}
          </div>
        </fieldset>

        <label className="field">
          <span className="label">
            Tell us more <span className="subtle font-normal">(optional)</span>
          </span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="What happened? The more detail, the faster we can help."
            className="input"
          />
        </label>

        {needsPhoto ? (
          <div className="flex flex-col gap-2 text-sm">
            <span className="label">Photo <span className="subtle font-normal">(needed for this reason)</span></span>
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-zinc-300 bg-zinc-50/60 px-4 py-6 text-center transition-colors hover:border-indigo-400 hover:bg-indigo-50/40 dark:border-zinc-700 dark:bg-zinc-900">
              {preview ? (
                // A local preview of the chosen file (a blob: URL), not a remote image.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Your photo" className="max-h-48 w-fit rounded-lg border border-zinc-200 shadow-sm" />
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-8 w-8 text-zinc-400">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5V18a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-1.5M16 8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              )}
              <span className="font-medium text-indigo-600 dark:text-indigo-400">{photo ? "Choose a different photo" : "Choose a photo"}</span>
              <span className="hint">Show the damage or problem clearly. JPEG, PNG or WebP, up to {MAX_PHOTO_MB} MB. We remove location data.</span>
              <input type="file" accept={ACCEPTED} onChange={(e) => onPhoto(e.target.files?.[0])} className="sr-only" />
            </label>
            {!photo ? (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                You can submit now and add the photo later, but we can&apos;t review your return until you do.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="card card-pad flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm">
          <span className="muted">Refund if approved</span>
          <span className="block text-xl font-semibold tabular-nums">{formatMoney(item.unit_price_cents * item.quantity)}</span>
          <span className="subtle text-xs">To the card ending {order.card_last4}</span>
        </p>
        <button type="submit" disabled={!ready} className="btn btn-primary btn-lg">
          {pending ? "Submitting…" : "Submit return"}
        </button>
      </div>
      {error ? <ErrorNotice>{error}</ErrorNotice> : null}
    </form>
  );
}
