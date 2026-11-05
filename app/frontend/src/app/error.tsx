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
    <section className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-3 py-20 text-center">
      <p className="text-sm font-medium text-red-700 dark:text-red-400">Something went wrong</p>
      <h1 className="text-2xl font-semibold">We hit a snag loading this page</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Nothing was lost — try again, or head back and pick up where you left off.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm text-white hover:opacity-90 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Try again
        </button>
        <Link href="/" className="rounded-md border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">
          Go home
        </Link>
      </div>
    </section>
  );
}
