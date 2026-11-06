import { Logo } from "@/components/logo";

/** The centered card used by the sign-in and sign-up pages. */
export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-4">
      <div className="card px-6 py-8 sm:px-8">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <Logo className="h-11 w-11" />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
          </div>
        </div>
        {children}
      </div>
      {footer ? <div className="mt-5 text-center text-sm muted">{footer}</div> : null}
    </div>
  );
}
