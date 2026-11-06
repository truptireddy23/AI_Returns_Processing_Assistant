import Link from "next/link";

/** Title, optional subtitle and back link, and actions on the right. */
export function PageHeader({
  title,
  subtitle,
  actions,
  back,
  eyebrow,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  back?: { href: string; label: string };
  eyebrow?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3">
      {back ? (
        <Link href={back.href} className="subtle w-fit text-sm hover:text-zinc-900 dark:hover:text-zinc-100">
          ← {back.label}
        </Link>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {eyebrow ? <div className="mb-1.5">{eyebrow}</div> : null}
          <h1 className="page-title">{title}</h1>
          {subtitle ? <div className="page-subtitle">{subtitle}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}

/** Placeholder rows while data loads. */
export function LoadingRows({ rows = 3, label = "Loading…" }: { rows?: number; label?: string }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton h-16 w-full" />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

/** A friendly empty state with an optional action. */
export function EmptyState({
  title,
  body,
  action,
  testId,
}: {
  title: string;
  body?: React.ReactNode;
  action?: React.ReactNode;
  testId?: string;
}) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-12 text-center" data-testid={testId}>
      <span className="mb-1 flex h-11 w-11 items-center justify-center rounded-full bg-zinc-100 text-zinc-400 dark:bg-zinc-800">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} className="h-5 w-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 7l1.5 12h13L20 7M4 7l2-3h12l2 3M9.5 11h5" />
        </svg>
      </span>
      <p className="font-medium">{title}</p>
      {body ? <p className="muted max-w-sm text-sm">{body}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

/** An error line with the alert role. */
export function ErrorNotice({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="notice notice-danger">
      {children}
    </p>
  );
}
