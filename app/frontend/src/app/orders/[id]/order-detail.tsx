"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import { ErrorNotice, LoadingRows, PageHeader } from "@/components/ui";
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
      <div className="flex flex-col gap-3">
        <ErrorNotice>{error}</ErrorNotice>
        <Link href="/orders" className="link w-fit text-sm">Back to my orders</Link>
      </div>
    );
  }
  if (!order) return <LoadingRows rows={4} />;

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-6" data-testid="order-detail">
      <PageHeader
        back={{ href: "/orders", label: "All orders" }}
        title={`Order #${order.order_number}`}
        subtitle={`Placed ${formatDateTime(order.placed_at)}`}
        actions={<span className="text-2xl font-semibold tabular-nums">{formatMoney(order.total_cents)}</span>}
      />

      <div className="card overflow-hidden">
        <div className="card-header"><h2 className="font-semibold">Items</h2></div>
        <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {order.items.map((i) => (
            <li key={i.id} className="flex flex-wrap items-center gap-4 px-5 py-4" data-testid={`detail-item-${i.id}`}>
              {i.photo_url ? <Image src={i.photo_url} alt="" width={64} height={64} unoptimized className="h-16 w-16 rounded-lg border border-zinc-100 bg-white object-contain p-1 dark:border-zinc-800" /> : null}
              <span className="min-w-40 flex-1">
                <span className="font-medium">{i.product_name}</span>
                {i.is_final_sale ? <span className="badge badge-warning ml-2">Final Sale</span> : null}
                <span className="subtle block text-xs">
                  {i.quantity} × {formatMoney(i.unit_price_cents)}
                </span>
              </span>
              <span className="w-20 text-right font-medium tabular-nums">{formatMoney(i.unit_price_cents * i.quantity)}</span>
              <span className="flex w-44 justify-end text-sm">
                {i.return_id && i.return_status ? (
                  <Link href={`/returns/${i.return_id}`} className="transition hover:opacity-80">
                    <StatusBadge status={i.return_status} />
                  </Link>
                ) : order.delivered_at ? (
                  <Link href={`/returns/new/${i.id}`} className="btn btn-secondary btn-sm">
                    Return item
                  </Link>
                ) : (
                  <span className="subtle">Returnable after delivery</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <dl className="card card-pad grid grid-cols-1 gap-x-8 gap-y-5 text-sm sm:grid-cols-2">
        <div>
          <dt className="eyebrow">Order ID</dt>
          <dd className="mt-1 font-mono text-xs break-all" data-testid="order-id">{order.id}</dd>
        </div>
        <div>
          <dt className="eyebrow">Ordered by</dt>
          <dd className="mt-1">
            {order.customer_name}
            <br />
            <span className="muted">{order.customer_email}</span>
          </dd>
        </div>
        <div>
          <dt className="eyebrow">Placed</dt>
          <dd className="mt-1" data-testid="placed-at">{formatDateTime(order.placed_at)}</dd>
        </div>
        <div>
          <dt className="eyebrow">Delivered</dt>
          <dd className="mt-1" data-testid="delivered-at">{order.delivered_at ? formatDateTime(order.delivered_at) : "Not delivered yet"}</dd>
        </div>
        <div>
          <dt className="eyebrow">Shipping address</dt>
          <dd className="mt-1"><AddressBlock address={order.shipping} /></dd>
        </div>
        <div>
          <dt className="eyebrow">Billing address</dt>
          <dd className="mt-1" data-testid="billing">
            {order.billing.same_as_shipping ? <span>Same as shipping address</span> : <AddressBlock address={order.billing} />}
          </dd>
        </div>
        <div>
          <dt className="eyebrow">Paid with</dt>
          <dd className="mt-1" data-testid="card">Card ending in {order.card_last4}</dd>
        </div>
        <div>
          <dt className="eyebrow">Total</dt>
          <dd className="mt-1 font-semibold">{formatMoney(order.total_cents)}</dd>
        </div>
      </dl>
    </section>
  );
}
