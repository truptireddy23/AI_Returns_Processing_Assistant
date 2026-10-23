"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { RequireRole } from "@/components/require-role";
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
  const ready = reason !== "" && (!needsPhoto || photo !== null) && !pending;

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

  if (found === undefined) return <p className="text-zinc-500">Loading…</p>;
  if (found === null) {
    return (
      <p role="alert">
        We couldn&apos;t find that item in your orders. <Link href="/orders" className="underline">Back to my orders</Link>
      </p>
    );
  }
  const { order, item } = found;
  if (item.return_id) {
    return (
      <p>
        You&apos;ve already started a return for this item.{" "}
        <Link href={`/returns/${item.return_id}`} className="underline">See its status</Link>
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto flex w-full max-w-xl flex-col gap-5" aria-label="Start a return">
      <h1 className="text-2xl font-semibold">Return an item — Order #{order.order_number}</h1>

      <div className="flex items-center gap-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
        {item.photo_url ? <Image src={item.photo_url} alt="" width={56} height={56} unoptimized className="rounded" /> : null}
        <span className="flex-1">{item.product_name}</span>
        <span>{formatMoney(item.unit_price_cents * item.quantity)}</span>
      </div>
      {item.is_final_sale ? (
        <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">
          This item was Final Sale. Final Sale items can only be returned if they arrived damaged, defective, or were the wrong item.
        </p>
      ) : null}

      <label className="flex flex-col gap-1 text-sm">
        Reason
        <select
          required
          value={reason}
          onChange={(e) => setReason(e.target.value as ReturnReason)}
          className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="" disabled>Choose a reason</option>
          {Object.entries(REASON_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Tell us more <span className="text-zinc-500">(optional)</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={1000}
          rows={3}
          className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>

      {needsPhoto ? (
        <div className="flex flex-col gap-2 text-sm">
          <label className="flex flex-col gap-1">
            Photo (required for this reason)
            <input type="file" accept={ACCEPTED} onChange={(e) => onPhoto(e.target.files?.[0])} />
          </label>
          <p className="text-xs text-zinc-500">
            Show the damage or problem clearly. JPEG, PNG or WebP, up to {MAX_PHOTO_MB} MB. We remove location data from photos.
          </p>
          {preview ? (
            // A local preview of the chosen file (a blob: URL), not a remote image.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Your photo" className="max-h-48 w-fit rounded border border-zinc-200" />
          ) : null}
        </div>
      ) : null}

      <p className="text-sm">
        Refund: <strong>{formatMoney(item.unit_price_cents * item.quantity)}</strong> to the card ending {order.card_last4}, if approved.
      </p>
      {error ? <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p> : null}
      <button
        type="submit"
        disabled={!ready}
        className="rounded-md bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {pending ? "Submitting…" : "Submit return"}
      </button>
    </form>
  );
}
