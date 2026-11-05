"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import { api, errorMessage, formatDate, formatMoney, type Order } from "@/lib/api";

export default function OrdersPage() {
  return <RequireRole roles={["customer"]}>{() => <MyOrders />}</RequireRole>;
}

function MyOrders() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/orders").then(({ data, error }) => {
      if (data) setOrders(data);
      else setError(errorMessage(error));
    });
  }, []);

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">My orders</h1>
      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {orders === null && !error ? <p className="text-zinc-500">Loading…</p> : null}
      {orders?.length === 0 ? (
        <p>
          No orders yet. <Link href="/shop" className="underline">Browse the shop</Link>.
        </p>
      ) : null}
      <ul className="flex flex-col gap-3" data-testid="orders">
        {orders?.map((o) => (
          <li key={o.id} className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <Link href={`/orders/${o.id}`} className="font-medium hover:underline" data-testid={`order-link-${o.order_number}`}>
                Order #{o.order_number} <span className="text-sm font-normal text-zinc-500">· View details</span>
              </Link>
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                {o.delivered_at ? `Delivered ${formatDate(o.delivered_at)}` : "Not delivered yet"} · Card •••• {o.card_last4}
              </span>
            </div>
            <ul className="mt-3 flex flex-col gap-3">
              {o.items.map((i) => (
                <li key={i.id} className="flex items-center gap-3" data-testid={`item-${i.id}`}>
                  {i.photo_url ? (
                    <Image src={i.photo_url} alt="" width={48} height={48} unoptimized className="rounded" />
                  ) : null}
                  <span className="flex-1">
                    {i.product_name}
                    {i.quantity > 1 ? ` × ${i.quantity}` : ""}
                    {i.is_final_sale ? <span className="ml-2 text-xs text-amber-700">Final Sale</span> : null}
                  </span>
                  <span className="w-20 text-right text-sm">{formatMoney(i.unit_price_cents * i.quantity)}</span>
                  <span className="w-40 text-right text-sm">
                    {i.return_id && i.return_status ? (
                      <Link href={`/returns/${i.return_id}`} className="hover:underline">
                        <StatusBadge status={i.return_status} />
                      </Link>
                    ) : o.delivered_at ? (
                      <Link href={`/returns/new/${i.id}`} className="underline">
                        Return item
                      </Link>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
