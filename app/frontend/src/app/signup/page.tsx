"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { useAuth } from "@/lib/auth";

const MIN_PASSWORD = 10;
const inputClass = "input";

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
    <AuthShell
      title="Create your account"
      subtitle="Shop and start returns online."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="link">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4" aria-label="Create an account">
        <label className="field">
          <span className="label">Name</span>
          <input name="display_name" required maxLength={100} autoComplete="name" className={inputClass} />
        </label>
        <label className="field">
          <span className="label">Email</span>
          <input name="email" type="email" required autoComplete="email" placeholder="you@example.com" className={inputClass} />
        </label>
        <label className="field">
          <span className="label">Password</span>
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
          <span id="password-help" className="hint">
            At least {MIN_PASSWORD} characters. Not your email, and not a common password.
          </span>
        </label>
        <label className="field">
          <span className="label">Confirm password</span>
          <input name="confirm" type="password" required autoComplete="new-password" className={inputClass} />
        </label>
        {error ? (
          <p role="alert" className="notice notice-danger">
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={pending} className="btn btn-primary mt-1 w-full py-2.5">
          {pending ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthShell>
  );
}
