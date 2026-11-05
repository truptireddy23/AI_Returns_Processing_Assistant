"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import { api, errorMessage, formatDateTime, formatMoney, type OrderDetail } from "@/lib/api";
import type { components } from "@/lib/api-schema";

type Address = components["schemas"]["Address"];

export function OrderDetailView() {
  return <RequireRole roles={["customer"]}>{() => <Detail />}</RequireRole>;
}

function AddressBlock({ address }: { address: Address }) {
  return (
    <address className="not-italic leading-6">
      {address.name}
      <br />
      {address.line1}
      <br />
      {address.city} {address.postal_code}
    </address>
  );
}

function Detail() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/orders/{order_id}", { params: { path: { order_id: id } } }).then(({ data, error }) => {
      if (data) setOrder(data);
      else setError(errorMessage(error, "We couldn't load this order."));
    });
  }, [id]);

  if (error) {
    return (
      <p role="alert" className="text-red-700">
        {error} <Link href="/orders" className="underline">Back to my orders</Link>
      </p>
    );
  }
  if (!order) return <p className="text-zinc-500">Loading…</p>;

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6" data-testid="order-detail">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">Order #{order.order_number}</h1>
        <Link href="/orders" className="text-sm underline">All orders</Link>
      </div>

      <dl className="grid grid-cols-1 gap-x-8 gap-y-4 rounded-md border border-zinc-200 p-4 text-sm sm:grid-cols-2 dark:border-zinc-800">
        <div>
          <dt className="text-zinc-500">Order ID</dt>
          <dd className="font-mono text-xs break-all" data-testid="order-id">{order.id}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Ordered by</dt>
          <dd>
            {order.customer_name}
            <br />
            <span className="text-zinc-600 dark:text-zinc-400">{order.customer_email}</span>
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Placed</dt>
          <dd data-testid="placed-at">{formatDateTime(order.placed_at)}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Delivered</dt>
          <dd data-testid="delivered-at">{order.delivered_at ? formatDateTime(order.delivered_at) : "Not delivered yet"}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Shipping address</dt>
          <dd><AddressBlock address={order.shipping} /></dd>
        </div>
        <div>
          <dt className="text-zinc-500">Billing address</dt>
          <dd data-testid="billing">
            {order.billing.same_as_shipping ? (
              <span>Same as shipping address</span>
            ) : (
              <AddressBlock address={order.billing} />
            )}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500">Paid with</dt>
          <dd data-testid="card">Card ending in {order.card_last4}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Total</dt>
          <dd className="font-medium">{formatMoney(order.total_cents)}</dd>
        </div>
      </dl>

      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Items</h2>
        <ul className="flex flex-col divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {order.items.map((i) => (
            <li key={i.id} className="flex flex-wrap items-center gap-3 p-3" data-testid={`detail-item-${i.id}`}>
              {i.photo_url ? <Image src={i.photo_url} alt="" width={56} height={56} unoptimized className="rounded" /> : null}
              <span className="min-w-40 flex-1">
                {i.product_name}
                {i.is_final_sale ? <span className="ml-2 text-xs text-amber-700">Final Sale</span> : null}
                <span className="block text-xs text-zinc-500">
                  {i.quantity} × {formatMoney(i.unit_price_cents)}
                </span>
              </span>
              <span className="w-20 text-right">{formatMoney(i.unit_price_cents * i.quantity)}</span>
              <span className="w-40 text-right text-sm">
                {i.return_id && i.return_status ? (
                  <Link href={`/returns/${i.return_id}`} className="hover:underline">
                    <StatusBadge status={i.return_status} />
                  </Link>
                ) : order.delivered_at ? (
                  <Link
                    href={`/returns/new/${i.id}`}
                    className="rounded-md border border-zinc-300 px-3 py-1.5 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
                  >
                    Return item
                  </Link>
                ) : (
                  <span className="text-zinc-500">Returnable after delivery</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
