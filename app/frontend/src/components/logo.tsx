/** The ReturnGuard mark: a shield with a check. */
export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`flex items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-sm ${className}`}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} className="h-[60%] w-[60%]">
        <path strokeLinejoin="round" d="M12 3l7 3v5.5c0 4.3-2.9 7.9-7 9.5-4.1-1.6-7-5.2-7-9.5V6l7-3Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2.2 2.2L15.5 10" />
      </svg>
    </span>
  );
}
