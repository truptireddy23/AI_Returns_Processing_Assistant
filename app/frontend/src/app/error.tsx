"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // The server already logged this (correlation id in asgi-correlation-id's
    // response header); this is just so it's not silently swallowed client-side.
    console.error(error);
  }, [error]);

  return (
    <section className="card mx-auto my-auto flex w-full max-w-md flex-col items-center gap-3 px-8 py-14 text-center">
      <p className="badge badge-danger">Something went wrong</p>
      <h1 className="text-2xl font-semibold">We hit a snag loading this page</h1>
      <p className="muted">
        Nothing was lost — try again, or head back and pick up where you left off.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="btn btn-primary"
        >
          Try again
        </button>
        <Link href="/" className="btn btn-secondary">
          Go home
        </Link>
      </div>
    </section>
  );
}
