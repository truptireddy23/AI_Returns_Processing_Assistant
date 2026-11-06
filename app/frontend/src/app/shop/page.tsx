"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductGallery } from "@/components/product-gallery";
import { ErrorNotice, PageHeader } from "@/components/ui";

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
      <PageHeader
        title="Shop"
        subtitle="Everyday essentials, with returns reviewed fairly and fast."
        actions={
          <div role="group" aria-label="Filter by category" className="tabs">
            {CATEGORIES.map((c) => (
              <button key={c} type="button" aria-pressed={category === c} onClick={() => setCategory(c)} className="tab capitalize">
                {c}
              </button>
            ))}
          </div>
        }
      />

      {error ? <ErrorNotice>{error}</ErrorNotice> : null}
      {!products && !error ? (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading">
          {Array.from({ length: 6 }, (_, i) => <div key={i} className="skeleton aspect-[4/5] w-full rounded-xl" />)}
        </div>
      ) : null}

      <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3" data-testid="catalog">
        {shown?.map((p) => (
          <li
            key={p.id}
            className="card group flex flex-col overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
          >
            <ProductGallery product={p} />
            <div className="flex flex-1 flex-col gap-2 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="eyebrow">{p.category}</p>
                  <h2 className="mt-0.5 font-semibold leading-snug">{p.name}</h2>
                </div>
                <span className="text-lg font-semibold tabular-nums">{formatMoney(p.price_cents)}</span>
              </div>
              <p className="muted line-clamp-3 text-sm">{p.description}</p>
              {p.is_final_sale ? <span className="badge badge-warning w-fit">Final Sale · not returnable</span> : null}
              <div className="mt-auto pt-3">
                {isCustomer ? (
                  <button type="button" onClick={() => addToCart(p)} className={`btn w-full ${justAdded === p.id ? "btn-success" : "btn-primary"}`}>
                    {justAdded === p.id ? "Added ✓" : "Add to cart"}
                  </button>
                ) : auth.status === "signed_out" ? (
                  <Link href="/login" className="btn btn-secondary w-full">
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
