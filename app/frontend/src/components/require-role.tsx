"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { Role, User } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Shows `children` only to signed-in users holding one of `roles`.
 * The API enforces roles on every endpoint; this only keeps the UI tidy.
 */
export function RequireRole({
  roles,
  children,
}: {
  roles: Role[];
  children: (user: User) => React.ReactNode;
}) {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === "signed_out") router.replace("/login");
  }, [auth.status, router]);

  if (auth.status !== "signed_in") {
    return <p className="text-zinc-500">Loading…</p>;
  }
  if (!roles.includes(auth.user.role)) {
    return (
      <div role="alert" className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">You don&apos;t have access to this page</h1>
        <p className="text-zinc-600 dark:text-zinc-400">
          You&apos;re signed in as {auth.user.display_name} ({auth.user.role}).{" "}
          <Link href="/" className="underline">
            Go home
          </Link>
        </p>
      </div>
    );
  }
  return <>{children(auth.user)}</>;
}
