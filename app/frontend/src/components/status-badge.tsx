import { STATUS_LABELS, type ReturnStatus } from "@/lib/api";

const TONE: Record<ReturnStatus, string> = {
  needs_info: "bg-amber-100 text-amber-900",
  submitted: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100",
  checking: "bg-sky-100 text-sky-900",
  under_review: "bg-violet-100 text-violet-900",
  failed: "bg-violet-100 text-violet-900",
  approved: "bg-green-100 text-green-900",
  denied: "bg-red-100 text-red-900",
};

export function StatusBadge({ status }: { status: ReturnStatus }) {
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs ${TONE[status]}`} data-status={status}>
      {STATUS_LABELS[status]}
    </span>
  );
}
