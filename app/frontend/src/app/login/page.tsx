"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    setPending(true);
    setError(null);
    const result = await auth.login(String(form.get("email")), String(form.get("password")));
    setPending(false);
    if (result.ok) {
      // Next.js keeps visited pages alive in the background, so clear the
      // credentials before leaving; otherwise the next person to open the
      // sign-in page on this device would find them filled in.
      formEl.reset();
      router.push(homeFor(result.user.role));
    } else {
      setError(result.message);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-6">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input
            name="email"
            type="email"
            autoComplete="username"
            required
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        {error ? (
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {pending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="text-xs text-zinc-500">Demo accounts are listed in app/seed/users.json.</p>
    </div>
  );
}
