import {
  DECISION_LABELS,
  ESCALATION_LABELS,
  STRENGTH_LABELS,
  type Decision,
  type EscalationReason,
  type EvidenceStrength,
} from "@/lib/api";

const NONE = <span className="text-zinc-400">—</span>;

const DECISION_TONE: Record<Decision, string> = {
  approve: "badge-success",
  deny: "badge-danger",
  escalate: "badge-neutral",
};

/** The AI's proposal (or, with `final`, a person's decision). */
export function DecisionBadge({ decision, final = false }: { decision: Decision | null; final?: boolean }) {
  if (!decision) return NONE;
  const label = final ? (decision === "approve" ? "Approved" : decision === "deny" ? "Denied" : "Escalated") : DECISION_LABELS[decision];
  return (
    <span className={`badge ${DECISION_TONE[decision]}`} data-decision={decision}>
      {label}
    </span>
  );
}

const STRENGTH_TONE: Record<EvidenceStrength, string> = {
  strong: "badge-success",
  mixed: "badge-warning",
  weak: "badge-danger",
};

const STRENGTH_BARS: Record<EvidenceStrength, number> = { strong: 3, mixed: 2, weak: 1 };

/** Evidence strength is computed from the checks, never the model's self-rating (M3). */
export function StrengthBadge({ strength }: { strength: EvidenceStrength | null }) {
  if (!strength) return NONE;
  const filled = STRENGTH_BARS[strength];
  return (
    <span className={`badge ${STRENGTH_TONE[strength]}`}>
      <span aria-hidden className="flex items-end gap-px">
        {[1, 2, 3].map((n) => (
          <span key={n} className={`w-[3px] rounded-sm bg-current ${n <= filled ? "" : "opacity-25"}`} style={{ height: 4 + n * 2 }} />
        ))}
      </span>
      {STRENGTH_LABELS[strength]}
    </span>
  );
}

const URGENT: EscalationReason[] = ["proposed_denial", "unverified_photo", "ambiguous_call", "critic_concern", "pipeline_error"];

/** "Why here": one of the gate's named reasons (M2). */
export function ReasonBadge({ reason }: { reason: EscalationReason | null }) {
  if (!reason) return NONE;
  const tone = URGENT.includes(reason) ? "badge-warning" : reason === "customer_requested_review" ? "badge-violet" : "badge-neutral";
  return (
    <span className={`badge ${tone}`} data-reason={reason}>
      {ESCALATION_LABELS[reason]}
    </span>
  );
}
