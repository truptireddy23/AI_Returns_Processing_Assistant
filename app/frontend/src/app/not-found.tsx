import Link from "next/link";

export default function NotFound() {
  return (
    <section className="mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-3 py-20 text-center">
      <p className="text-sm font-medium text-zinc-500">404</p>
      <h1 className="text-2xl font-semibold">We couldn&apos;t find that page</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        The link might be out of date, or the page may have moved.
      </p>
      <Link
        href="/"
        className="mt-3 rounded-md bg-zinc-900 px-4 py-2 text-sm text-white hover:opacity-90 dark:bg-zinc-100 dark:text-zinc-900"
      >
        Back to ReturnGuard
      </Link>
    </section>
  );
}
