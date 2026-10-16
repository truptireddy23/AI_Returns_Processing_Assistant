"use client";

import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { api, errorMessage, formatDate, formatMoney } from "@/lib/api";
import type { components } from "@/lib/api-schema";

type Order = components["schemas"]["OrderOut"];

export default function ShopPage() {
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
      {orders?.length === 0 ? <p>You have no orders yet.</p> : null}
      <ul className="flex flex-col gap-3" data-testid="orders">
        {orders?.map((o) => (
          <li key={o.id} className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium">Order #{o.order_number}</span>
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                {o.delivered_at ? `Delivered ${formatDate(o.delivered_at)}` : "Not delivered yet"}
              </span>
            </div>
            <ul className="mt-2 text-sm">
              {o.items.map((i) => (
                <li key={i.id} className="flex justify-between gap-2">
                  <span>
                    {i.product_name}
                    {i.is_final_sale ? <span className="ml-2 text-xs text-amber-700">Final Sale</span> : null}
                  </span>
                  <span>{formatMoney(i.unit_price_cents)}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
