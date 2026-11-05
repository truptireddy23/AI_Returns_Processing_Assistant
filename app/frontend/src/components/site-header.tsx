"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

const ROLE_LABEL = { customer: "Customer", reviewer: "Reviewer", admin: "Admin" } as const;

export function SiteHeader() {
  const auth = useAuth();
  const cart = useCart();
  const router = useRouter();
  const pathname = usePathname();
  const [signOutFailed, setSignOutFailed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // A route change (including the signed-out redirect below) always means the
  // menu should close, so a stale open panel never covers the new page. Adjusted
  // during render (not an effect) per https://react.dev/learn/you-might-not-need-an-effect.
  const [lastPathname, setLastPathname] = useState(pathname);
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setMenuOpen(false);
  }

  async function signOut() {
    setSignOutFailed(false);
    if (await auth.logout()) router.push("/login");
    else setSignOutFailed(true);
  }

  const links =
    auth.status === "signed_in" ? (
      auth.user.role === "customer" ? (
        <>
          <Link href="/shop" className="hover:underline">Shop</Link>
          <Link href="/cart" className="hover:underline" data-testid="cart-link">
            Cart{cart.count > 0 ? ` (${cart.count})` : ""}
          </Link>
          <Link href="/orders" className="hover:underline">My orders</Link>
        </>
      ) : (
        <>
          {/* Admins hold every reviewer right, so they get the queue too. */}
          <Link href="/review" className="hover:underline">Review queue</Link>
          {auth.user.role === "admin" ? (
            <Link href={homeFor(auth.user.role)} className="hover:underline">Admin</Link>
          ) : null}
        </>
      )
    ) : auth.status === "signed_out" ? (
      <>
        <Link href="/shop" className="hover:underline">Shop</Link>
        <Link href="/login" className="hover:underline">Sign in</Link>
        <Link href="/signup" className="rounded bg-zinc-900 px-2 py-1 text-white hover:opacity-90 dark:bg-zinc-100 dark:text-zinc-900">
          Create account
        </Link>
      </>
    ) : null;

  const account =
    auth.status === "signed_in" ? (
      <>
        <span className="text-zinc-600 dark:text-zinc-400" data-testid="signed-in-as">
          {auth.user.display_name}
          <span className="ml-2 rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800">
            {ROLE_LABEL[auth.user.role]}
          </span>
        </span>
        <button
          type="button"
          onClick={signOut}
          className="rounded px-2 py-1 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800"
        >
          Sign out
        </button>
        {signOutFailed ? (
          <span role="alert" className="text-red-700 dark:text-red-400">
            Couldn&apos;t sign you out. Please try again.
          </span>
        ) : null}
      </>
    ) : null;

  if (auth.status !== "signed_in" && auth.status !== "signed_out") {
    return (
      <header className="border-b border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/" className="font-semibold tracking-tight">
            ReturnGuard
          </Link>
        </div>
      </header>
    );
  }

  return (
    <header className="relative border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-semibold tracking-tight">
          ReturnGuard
        </Link>

        {/* Desktop: everything in one row. */}
        <nav className="hidden items-center gap-4 text-sm sm:flex" aria-label="Account">
          {links}
          {account}
        </nav>

        {/* Mobile: a single toggle; the links drop down below the header. */}
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
          className="rounded p-2 hover:bg-zinc-100 sm:hidden dark:hover:bg-zinc-800"
        >
          <span className="sr-only">{menuOpen ? "Close menu" : "Open menu"}</span>
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-5 w-5">
            {menuOpen ? (
              <path strokeLinecap="round" d="M5 5l10 10M15 5L5 15" />
            ) : (
              <path strokeLinecap="round" d="M3 5h14M3 10h14M3 15h14" />
            )}
          </svg>
        </button>
      </div>

      {menuOpen ? (
        <nav
          id="mobile-nav"
          aria-label="Account"
          className="flex flex-col gap-1 border-t border-zinc-200 px-4 py-3 text-sm sm:hidden dark:border-zinc-800"
        >
          {links}
          {account ? <div className="mt-2 flex flex-col gap-1 border-t border-zinc-200 pt-2 dark:border-zinc-800">{account}</div> : null}
        </nav>
      ) : null}
    </header>
  );
}
