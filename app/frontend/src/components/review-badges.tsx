import {
  DECISION_LABELS,
  ESCALATION_LABELS,
  STRENGTH_LABELS,
  type Decision,
  type EscalationReason,
  type EvidenceStrength,
} from "@/lib/api";

const BASE = "inline-block rounded px-1.5 py-0.5 text-xs font-medium";

const DECISION_TONE: Record<Decision, string> = {
  approve: "bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-200",
  deny: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
  escalate: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100",
};

/** The AI's proposal (or, with `final`, a person's decision). */
export function DecisionBadge({ decision, final = false }: { decision: Decision | null; final?: boolean }) {
  if (!decision) return <span className="text-zinc-400">—</span>;
  const label = final ? (decision === "approve" ? "Approved" : decision === "deny" ? "Denied" : "Escalated") : DECISION_LABELS[decision];
  return <span className={`${BASE} ${DECISION_TONE[decision]}`} data-decision={decision}>{label}</span>;
}

const STRENGTH_TONE: Record<EvidenceStrength, string> = {
  strong: "bg-green-100 text-green-900 dark:bg-green-950 dark:text-green-200",
  mixed: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  weak: "bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200",
};

/** Evidence strength is computed from the checks, never the model's self-rating (M3). */
export function StrengthBadge({ strength }: { strength: EvidenceStrength | null }) {
  if (!strength) return <span className="text-zinc-400">—</span>;
  return <span className={`${BASE} ${STRENGTH_TONE[strength]}`}>{STRENGTH_LABELS[strength]}</span>;
}

const URGENT: EscalationReason[] = ["proposed_denial", "unverified_photo", "ambiguous_call", "critic_concern", "pipeline_error"];

/** "Why here": one of the gate's named reasons (M2). */
export function ReasonBadge({ reason }: { reason: EscalationReason | null }) {
  if (!reason) return <span className="text-zinc-400">—</span>;
  const tone = URGENT.includes(reason)
    ? "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200"
    : reason === "customer_requested_review"
      ? "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200"
      : "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100";
  return <span className={`${BASE} ${tone}`} data-reason={reason}>{ESCALATION_LABELS[reason]}</span>;
}
