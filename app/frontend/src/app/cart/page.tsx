"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { EmptyState, ErrorNotice, PageHeader } from "@/components/ui";
import { api, errorMessage, formatMoney, type Product } from "@/lib/api";
import { MAX_QUANTITY, useCart } from "@/lib/cart";

export default function CartPage() {
  return <RequireRole roles={["customer"]}>{() => <Cart />}</RequireRole>;
}

const inputClass = "input";

function Cart() {
  const cart = useCart();
  const router = useRouter();
  const [products, setProducts] = useState<Record<string, Product>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [billingSame, setBillingSame] = useState(true);

  useEffect(() => {
    api.GET("/api/products").then(({ data }) => {
      if (data) setProducts(Object.fromEntries(data.map((p) => [p.id, p])));
    });
  }, []);

  const lines = Object.entries(cart.lines).filter(([id]) => products[id]);
  const total = lines.reduce((sum, [id, q]) => sum + products[id].price_cents * q, 0);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const [month, year] = String(f.get("expiry")).split("/").map((v) => Number.parseInt(v.trim(), 10));
    setPending(true);
    setError(null);
    const { data, error } = await api.POST("/api/orders", {
      body: {
        items: lines.map(([product_id, quantity]) => ({ product_id, quantity })),
        shipping: {
          name: String(f.get("name")),
          line1: String(f.get("line1")),
          city: String(f.get("city")),
          postal_code: String(f.get("postal_code")),
        },
        billing: billingSame
          ? null
          : {
              name: String(f.get("billing_name")),
              line1: String(f.get("billing_line1")),
              city: String(f.get("billing_city")),
              postal_code: String(f.get("billing_postal_code")),
            },
        card: {
          number: String(f.get("card")),
          exp_month: month || 0,
          exp_year: year < 100 ? 2000 + year : year || 0,
          cvc: String(f.get("cvc")),
        },
      },
    });
    setPending(false);
    if (!data) {
      setError(errorMessage(error, "Checkout failed."));
      return;
    }
    cart.clear();
    router.push("/orders");
  }

  if (cart.count === 0) {
    return (
      <section className="flex flex-col gap-6">
        <PageHeader title="Cart" />
        <EmptyState
          title="Your cart is empty"
          body="Find something you like in the shop, then come back here to check out."
          action={<Link href="/shop" className="btn btn-primary">Browse the shop</Link>}
        />
      </section>
    );
  }

  const itemCount = lines.reduce((n, [, q]) => n + q, 0);

  return (
    <section className="flex flex-col gap-6">
      <PageHeader title="Cart" subtitle={`${itemCount} item${itemCount === 1 ? "" : "s"} ready for checkout`} />
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_minmax(0,24rem)]">
        <div className="card overflow-hidden">
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800" data-testid="cart-lines">
            {lines.map(([id, qty]) => {
              const p = products[id];
              const photo = p.photos[0]?.url ?? p.photo_url;
              return (
                <li key={id} className="flex items-center gap-4 p-4">
                  {photo ? (
                    <Image src={photo} alt="" width={64} height={64} unoptimized className="h-16 w-16 shrink-0 rounded-lg border border-zinc-100 bg-white object-contain p-1 dark:border-zinc-800" />
                  ) : null}
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{p.name}</p>
                    <p className="subtle text-sm">{formatMoney(p.price_cents)} each</p>
                  </div>
                  <label className="sr-only" htmlFor={`qty-${id}`}>Quantity</label>
                  <select
                    id={`qty-${id}`}
                    value={qty}
                    onChange={(e) => cart.setQuantity(id, Number(e.target.value))}
                    className="input w-24"
                  >
                    {Array.from({ length: MAX_QUANTITY + 1 }, (_, n) => (
                      <option key={n} value={n}>{n === 0 ? "Remove" : `Qty ${n}`}</option>
                    ))}
                  </select>
                  <span className="w-20 text-right font-medium tabular-nums">{formatMoney(p.price_cents * qty)}</span>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center justify-between border-t border-zinc-100 bg-zinc-50/60 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900/60">
            <span className="muted text-sm">Subtotal</span>
            <span className="text-lg font-semibold tabular-nums">{formatMoney(total)}</span>
          </div>
        </div>

        <form onSubmit={onSubmit} className="card card-pad flex flex-col gap-5 lg:sticky lg:top-24" aria-label="Checkout">
          <h2 className="text-lg font-semibold">Checkout</h2>
          <fieldset className="flex flex-col gap-2.5">
            <legend className="label mb-2">Shipping</legend>
            <input name="name" required placeholder="Full name" autoComplete="name" className={inputClass} />
            <input name="line1" required placeholder="Street address" autoComplete="address-line1" className={inputClass} />
            <div className="flex gap-2">
              <input name="city" required placeholder="City" autoComplete="address-level2" className={`${inputClass} flex-1`} />
              <input name="postal_code" required placeholder="ZIP" autoComplete="postal-code" className={`${inputClass} w-28`} />
            </div>
          </fieldset>
          <fieldset className="flex flex-col gap-2.5">
            <legend className="label mb-2">Billing</legend>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={billingSame} onChange={(e) => setBillingSame(e.target.checked)} className="checkbox" />
              Billing address same as shipping
            </label>
            {billingSame ? null : (
              <>
                <input name="billing_name" required placeholder="Name on card" autoComplete="billing name" className={inputClass} />
                <input name="billing_line1" required placeholder="Billing street address" autoComplete="billing address-line1" className={inputClass} />
                <div className="flex gap-2">
                  <input name="billing_city" required placeholder="City" autoComplete="billing address-level2" className={`${inputClass} flex-1`} />
                  <input name="billing_postal_code" required placeholder="ZIP" autoComplete="billing postal-code" className={`${inputClass} w-28`} />
                </div>
              </>
            )}
          </fieldset>
          <fieldset className="flex flex-col gap-2.5">
            <legend className="label mb-2">Payment <span className="badge badge-info ml-1">Test cards only</span></legend>
            <p className="hint">No money moves. Use 4242 4242 4242 4242, any future expiry, any 3-digit code.</p>
            <input name="card" required inputMode="numeric" placeholder="Card number" autoComplete="off" className={inputClass} />
            <div className="flex gap-2">
              <input name="expiry" required placeholder="MM/YY" autoComplete="off" className={`${inputClass} flex-1`} />
              <input name="cvc" required inputMode="numeric" placeholder="CVC" autoComplete="off" className={`${inputClass} w-28`} />
            </div>
          </fieldset>
          {error ? <ErrorNotice>{error}</ErrorNotice> : null}
          <button type="submit" disabled={pending} className="btn btn-primary w-full py-2.5">
            {pending ? "Placing order…" : `Place order · ${formatMoney(total)}`}
          </button>
        </form>
      </div>
    </section>
  );
}
