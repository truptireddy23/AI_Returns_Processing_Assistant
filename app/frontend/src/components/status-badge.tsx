import { STATUS_LABELS, type ReturnStatus } from "@/lib/api";

const TONE: Record<ReturnStatus, string> = {
  needs_info: "badge-warning",
  submitted: "badge-neutral",
  checking: "badge-info",
  under_review: "badge-violet",
  failed: "badge-violet",
  approved: "badge-success",
  denied: "badge-danger",
};

const DOT: Record<ReturnStatus, string> = {
  needs_info: "bg-amber-500",
  submitted: "bg-zinc-400",
  checking: "bg-sky-500 animate-pulse",
  under_review: "bg-violet-500",
  failed: "bg-violet-500",
  approved: "bg-emerald-500",
  denied: "bg-red-500",
};

export function StatusBadge({ status }: { status: ReturnStatus }) {
  return (
    <span className={`badge ${TONE[status]}`} data-status={status}>
      <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${DOT[status]}`} />
      {STATUS_LABELS[status]}
    </span>
  );
}
