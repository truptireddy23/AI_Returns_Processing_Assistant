"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { api, errorMessage, formatMoney, type Product } from "@/lib/api";
import { MAX_QUANTITY, useCart } from "@/lib/cart";

export default function CartPage() {
  return <RequireRole roles={["customer"]}>{() => <Cart />}</RequireRole>;
}

const inputClass = "rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900";

function Cart() {
  const cart = useCart();
  const router = useRouter();
  const [products, setProducts] = useState<Record<string, Product>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
      <section className="flex flex-col gap-3">
        <h1 className="text-2xl font-semibold">Cart</h1>
        <p>
          Your cart is empty. <Link href="/shop" className="underline">Browse the shop</Link>.
        </p>
      </section>
    );
  }

  return (
    <section className="grid gap-8 md:grid-cols-[1fr_minmax(0,22rem)]">
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">Cart</h1>
        <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800" data-testid="cart-lines">
          {lines.map(([id, qty]) => (
            <li key={id} className="flex items-center justify-between gap-3 py-3">
              <span>{products[id].name}</span>
              <span className="flex items-center gap-3">
                <label className="sr-only" htmlFor={`qty-${id}`}>Quantity</label>
                <select
                  id={`qty-${id}`}
                  value={qty}
                  onChange={(e) => cart.setQuantity(id, Number(e.target.value))}
                  className={inputClass}
                >
                  {Array.from({ length: MAX_QUANTITY + 1 }, (_, n) => (
                    <option key={n} value={n}>{n === 0 ? "Remove" : n}</option>
                  ))}
                </select>
                <span className="w-20 text-right">{formatMoney(products[id].price_cents * qty)}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="text-right font-medium">Total {formatMoney(total)}</p>
      </div>

      <form onSubmit={onSubmit} className="flex flex-col gap-3" aria-label="Checkout">
        <h2 className="text-lg font-medium">Checkout</h2>
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">Shipping</legend>
          <input name="name" required placeholder="Full name" autoComplete="name" className={inputClass} />
          <input name="line1" required placeholder="Street address" autoComplete="address-line1" className={inputClass} />
          <div className="flex gap-2">
            <input name="city" required placeholder="City" autoComplete="address-level2" className={`${inputClass} flex-1`} />
            <input name="postal_code" required placeholder="ZIP" autoComplete="postal-code" className={`${inputClass} w-24`} />
          </div>
        </fieldset>
        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">Payment (test cards only)</legend>
          <p className="text-xs text-zinc-500">
            No money moves. Use 4242 4242 4242 4242, any future expiry, any 3-digit code.
          </p>
          <input name="card" required inputMode="numeric" placeholder="Card number" autoComplete="off" className={inputClass} />
          <div className="flex gap-2">
            <input name="expiry" required placeholder="MM/YY" autoComplete="off" className={`${inputClass} flex-1`} />
            <input name="cvc" required inputMode="numeric" placeholder="CVC" autoComplete="off" className={`${inputClass} w-24`} />
          </div>
        </fieldset>
        {error ? <p role="alert" className="text-sm text-red-700 dark:text-red-400">{error}</p> : null}
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {pending ? "Placing order…" : `Place order · ${formatMoney(total)}`}
        </button>
      </form>
    </section>
  );
}
