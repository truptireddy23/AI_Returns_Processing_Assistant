"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

const ROLE_LABEL = { customer: "Customer", reviewer: "Reviewer", admin: "Admin" } as const;

export function SiteHeader() {
  const auth = useAuth();
  const cart = useCart();
  const router = useRouter();
  const [signOutFailed, setSignOutFailed] = useState(false);

  async function signOut() {
    setSignOutFailed(false);
    if (await auth.logout()) router.push("/login");
    else setSignOutFailed(true);
  }

  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-semibold tracking-tight">
          ReturnGuard
        </Link>
        {auth.status === "signed_in" ? (
          <nav className="flex items-center gap-4 text-sm" aria-label="Account">
            {auth.user.role === "customer" ? (
              <>
                <Link href="/shop" className="hover:underline">Shop</Link>
                <Link href="/cart" className="hover:underline" data-testid="cart-link">
                  Cart{cart.count > 0 ? ` (${cart.count})` : ""}
                </Link>
                <Link href="/orders" className="hover:underline">My orders</Link>
              </>
            ) : (
              <Link href={homeFor(auth.user.role)} className="hover:underline">
                {auth.user.role === "reviewer" ? "Review queue" : "Admin"}
              </Link>
            )}
            <span className="text-zinc-600 dark:text-zinc-400" data-testid="signed-in-as">
              {auth.user.display_name}
              <span className="ml-2 rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800">
                {ROLE_LABEL[auth.user.role]}
              </span>
            </span>
            <button type="button" onClick={signOut} className="rounded px-2 py-1 hover:bg-zinc-100 dark:hover:bg-zinc-800">
              Sign out
            </button>
            {signOutFailed ? (
              <span role="alert" className="text-red-700 dark:text-red-400">
                Couldn&apos;t sign you out. Please try again.
              </span>
            ) : null}
          </nav>
        ) : auth.status === "signed_out" ? (
          <nav className="flex items-center gap-4 text-sm" aria-label="Account">
            <Link href="/shop" className="hover:underline">Shop</Link>
            <Link href="/login" className="hover:underline">Sign in</Link>
          </nav>
        ) : null}
      </div>
    </header>
  );
}
