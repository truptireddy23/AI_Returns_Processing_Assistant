"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth";

const MIN_PASSWORD = 10;
const inputClass = "rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900";

export default function SignupPage() {
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    const password = String(form.get("password"));
    if (password !== String(form.get("confirm"))) {
      setError("The passwords don't match.");
      return;
    }
    setPending(true);
    setError(null);
    const result = await auth.signup(
      String(form.get("email")).trim(),
      password,
      String(form.get("display_name")).trim(),
    );
    setPending(false);
    if (result.ok) {
      // Next.js keeps visited pages alive in the background: clear the password first.
      formEl.reset();
      router.push("/shop");
    } else {
      setError(result.message);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-sm flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Create an account</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">Shop and start returns online.</p>
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-4" aria-label="Create an account">
        <label className="flex flex-col gap-1 text-sm">
          Name
          <input name="display_name" required maxLength={100} autoComplete="name" className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input name="email" type="email" required autoComplete="email" className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            name="password"
            type="password"
            required
            minLength={MIN_PASSWORD}
            maxLength={200}
            autoComplete="new-password"
            aria-describedby="password-help"
            className={inputClass}
          />
          <span id="password-help" className="text-xs text-zinc-500">
            At least {MIN_PASSWORD} characters. Not your email, and not a common password.
          </span>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Confirm password
          <input name="confirm" type="password" required autoComplete="new-password" className={inputClass} />
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
          {pending ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="text-sm">
        Already have an account?{" "}
        <Link href="/login" className="underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
