"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthShell } from "@/components/auth-shell";
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
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to shop, follow a return, or review cases."
      footer={
        <>
          New here?{" "}
          <Link href="/signup" className="link">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <label className="field">
          <span className="label">Email</span>
          <input name="email" type="email" autoComplete="username" required placeholder="you@example.com" className="input" />
        </label>
        <label className="field">
          <span className="label">Password</span>
          <input name="password" type="password" autoComplete="current-password" required className="input" />
        </label>
        {error ? (
          <p role="alert" className="notice notice-danger">
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={pending} className="btn btn-primary mt-1 w-full py-2.5">
          {pending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="hint mt-5 text-center">Demo accounts are listed in app/seed/users.json.</p>
    </AuthShell>
  );
}
