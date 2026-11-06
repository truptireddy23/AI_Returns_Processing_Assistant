"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useState } from "react";

import { Logo } from "@/components/logo";
import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCart } from "@/lib/cart";

const ROLE_LABEL = { customer: "Customer", reviewer: "Reviewer", admin: "Admin" } as const;
const ROLE_TONE = { customer: "badge-neutral", reviewer: "badge-brand", admin: "badge-violet" } as const;

type NavItem = { href: string; label: string; badge?: number; testId?: string };

const linkBase = "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors";
const linkIdle = "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-zinc-50";
const linkActive = "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300";

function NavLinkContent({ item }: { item: NavItem }) {
  return (
    <>
      {item.label}
      {item.badge ? (
        <span className="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-indigo-600 px-1.5 text-[11px] font-semibold text-white">
          {item.badge}
        </span>
      ) : null}
    </>
  );
}

/** Highlights the current section. `usePathname` is a request-time API here
 * (Cache Components), so this lives inside <Suspense> with a plain fallback. */
function ActiveNavLink({ item }: { item: NavItem }) {
  const pathname = usePathname();
  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
  return (
    <Link href={item.href} aria-current={active ? "page" : undefined} className={`${linkBase} ${active ? linkActive : linkIdle}`} data-testid={item.testId}>
      <NavLinkContent item={item} />
    </Link>
  );
}

function NavLink({ item }: { item: NavItem }) {
  return (
    <Suspense
      fallback={
        <Link href={item.href} className={`${linkBase} ${linkIdle}`} data-testid={item.testId}>
          <NavLinkContent item={item} />
        </Link>
      }
    >
      <ActiveNavLink item={item} />
    </Suspense>
  );
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function SiteHeader() {
  const auth = useAuth();
  const cart = useCart();
  const router = useRouter();
  const [signOutFailed, setSignOutFailed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  async function signOut() {
    setSignOutFailed(false);
    if (await auth.logout()) router.push("/login");
    else setSignOutFailed(true);
  }

  const items: NavItem[] =
    auth.status === "signed_in"
      ? auth.user.role === "customer"
        ? [
            { href: "/shop", label: "Shop" },
            { href: "/cart", label: "Cart", badge: cart.count || undefined, testId: "cart-link" },
            { href: "/orders", label: "My orders" },
          ]
        : [
            // Admins hold every reviewer right, so they get the queue too.
            { href: "/review", label: "Review queue" },
            ...(auth.user.role === "admin" ? [{ href: homeFor(auth.user.role), label: "Admin" }] : []),
          ]
      : auth.status === "signed_out"
        ? [{ href: "/shop", label: "Shop" }]
        : [];

  const account =
    auth.status === "signed_in" ? (
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5" data-testid="signed-in-as">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-xs font-semibold text-white"
          >
            {initials(auth.user.display_name)}
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{auth.user.display_name}</span>
            <span className={`badge ${ROLE_TONE[auth.user.role]} mt-0.5 w-fit px-1.5 py-0 text-[10px]`}>{ROLE_LABEL[auth.user.role]}</span>
          </span>
        </div>
        <button type="button" onClick={signOut} className="btn btn-ghost btn-sm">
          Sign out
        </button>
        {signOutFailed ? (
          <span role="alert" className="error-text">
            Couldn&apos;t sign you out. Please try again.
          </span>
        ) : null}
      </div>
    ) : auth.status === "signed_out" ? (
      <div className="flex items-center gap-2">
        <Link href="/login" className="btn btn-ghost btn-sm">Sign in</Link>
        <Link href="/signup" className="btn btn-primary btn-sm">Create account</Link>
      </div>
    ) : null;

  return (
    <header className="sticky top-0 z-30 border-b border-zinc-200/80 bg-white/80 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            <Logo />
            <span className="text-[17px]">ReturnGuard</span>
          </Link>
          {items.length ? (
            <nav className="hidden items-center gap-1 sm:flex" aria-label="Main">
              {items.map((item) => <NavLink key={item.href} item={item} />)}
            </nav>
          ) : null}
        </div>

        <div className="hidden sm:block">{account}</div>

        {/* Mobile: a single toggle; the links drop down below the header. */}
        {auth.status === "signed_in" || auth.status === "signed_out" ? (
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            className="btn btn-ghost p-2 sm:hidden"
          >
            <span className="sr-only">{menuOpen ? "Close menu" : "Open menu"}</span>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-5 w-5">
              {menuOpen ? <path strokeLinecap="round" d="M5 5l10 10M15 5L5 15" /> : <path strokeLinecap="round" d="M3 5h14M3 10h14M3 15h14" />}
            </svg>
          </button>
        ) : null}
      </div>

      {menuOpen ? (
        <nav
          id="mobile-nav"
          aria-label="Main"
          // Closes on any click inside: every link navigates away and Sign out
          // leaves the signed-in view, so there's never a stale panel left open.
          onClick={() => setMenuOpen(false)}
          className="flex flex-col gap-1 border-t border-zinc-200 bg-white px-4 py-3 sm:hidden dark:border-zinc-800 dark:bg-zinc-950"
        >
          {items.map((item) => <NavLink key={item.href} item={item} />)}
          {account ? <div className="mt-2 border-t border-zinc-200 pt-3 dark:border-zinc-800">{account}</div> : null}
        </nav>
      ) : null}
    </header>
  );
}
