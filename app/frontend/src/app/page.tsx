"use client";

import Link from "next/link";

import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";

import { SystemStatus } from "./system-status";

export default function Home() {
  const auth = useAuth();
  return (
    <div className="flex max-w-2xl flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight">ReturnGuard</h1>
        <p className="text-zinc-600 dark:text-zinc-400">
          AI reviews clear-cut returns. A person owns every denial and every judgment call.
        </p>
        {auth.status === "signed_in" ? (
          <Link href={homeFor(auth.user.role)} className="underline">
            Continue as {auth.user.display_name}
          </Link>
        ) : auth.status === "signed_out" ? (
          <Link href="/login" className="underline">
            Sign in
          </Link>
        ) : null}
      </header>
      <SystemStatus />
    </div>
  );
}
