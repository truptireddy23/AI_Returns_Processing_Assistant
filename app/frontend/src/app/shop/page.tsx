"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api, errorMessage, formatMoney, type Product } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

const CATEGORIES = ["all", "footwear", "clothing", "electronics", "home"] as const;
type Category = (typeof CATEGORIES)[number];

export default function ShopPage() {
  const auth = useAuth();
  const cart = useCart();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<Category>("all");
  const [justAdded, setJustAdded] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/products").then(({ data, error }) => {
      if (data) setProducts(data);
      else setError(errorMessage(error, "Couldn't load the catalog."));
    });
  }, []);

  const shown = products?.filter((p) => category === "all" || p.category === category);
  const isCustomer = auth.status === "signed_in" && auth.user.role === "customer";

  function addToCart(p: Product) {
    cart.add(p.id);
    setJustAdded(p.id);
    setTimeout(() => setJustAdded((id) => (id === p.id ? null : id)), 1500);
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-2xl font-semibold">Shop</h1>
        <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
              className={`rounded-full border px-3 py-1 text-sm capitalize ${
                category === c
                  ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                  : "border-zinc-300 dark:border-zinc-700"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {error ? <p role="alert" className="text-red-700">{error}</p> : null}
      {!products && !error ? <p className="text-zinc-500">Loading…</p> : null}

      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="catalog">
        {shown?.map((p) => (
          <li key={p.id} className="flex flex-col overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
            {p.photo_url ? (
              <Image src={p.photo_url} alt={p.name} width={400} height={400} unoptimized className="aspect-square w-full object-cover" />
            ) : null}
            <div className="flex flex-1 flex-col gap-2 p-4">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-medium">{p.name}</h2>
                <span className="font-medium">{formatMoney(p.price_cents)}</span>
              </div>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">{p.description}</p>
              {p.is_final_sale ? (
                <span className="w-fit rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900">Final Sale — not returnable</span>
              ) : null}
              <div className="mt-auto pt-2">
                {isCustomer ? (
                  <button
                    type="button"
                    onClick={() => addToCart(p)}
                    className="w-full rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
                  >
                    {justAdded === p.id ? "Added ✓" : "Add to cart"}
                  </button>
                ) : auth.status === "signed_out" ? (
                  <Link href="/login" className="text-sm underline">
                    Sign in to buy
                  </Link>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
