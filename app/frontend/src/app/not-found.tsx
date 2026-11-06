import Link from "next/link";

export default function NotFound() {
  return (
    <section className="card mx-auto my-auto flex w-full max-w-md flex-col items-center gap-3 px-8 py-14 text-center">
      <p className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-5xl font-semibold text-transparent">404</p>
      <h1 className="text-2xl font-semibold">We couldn&apos;t find that page</h1>
      <p className="muted">
        The link might be out of date, or the page may have moved.
      </p>
      <Link
        href="/"
        className="btn btn-primary mt-3"
      >
        Back to ReturnGuard
      </Link>
    </section>
  );
}
