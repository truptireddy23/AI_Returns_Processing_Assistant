import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./api-schema";

export type User = components["schemas"]["UserOut"];
export type Role = User["role"];
export type Product = components["schemas"]["ProductOut"];
export type Order = components["schemas"]["OrderOut"];
export type OrderDetail = components["schemas"]["OrderDetailOut"];
export type OrderItem = components["schemas"]["OrderItemOut"];
export type ReturnCase = components["schemas"]["ReturnOut"];
export type ReturnReason = ReturnCase["reason"];
export type ReturnStatus = ReturnCase["status"];

// The CSRF token for the current session. Kept in memory only (never in
// storage) and attached to every state-changing request.
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

/** For requests made outside the typed client (e.g. multipart uploads). */
export function csrfHeaders(): Record<string, string> {
  return csrfToken ? { "X-CSRF-Token": csrfToken } : {};
}

const csrf: Middleware = {
  onRequest({ request }) {
    if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes(request.method)) {
      request.headers.set("X-CSRF-Token", csrfToken);
    }
    return request;
  },
};

// Same-origin: /api/* is proxied to FastAPI by src/app/api/[...path]/route.ts.
export const api = createClient<paths>({ baseUrl: "", credentials: "same-origin" });
api.use(csrf);

/** Pull a human-readable message out of a FastAPI error body. */
export function errorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return fallback;
}

export function homeFor(role: Role): string {
  return role === "customer" ? "/shop" : role === "reviewer" ? "/review" : "/admin";
}

export function formatMoney(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}

/** Date and time in the viewer's own time zone, e.g. "Oct 23, 2026, 3:42 PM CDT". */
export function formatDateTime(iso: string): string {
  // dateStyle/timeStyle can't be combined with timeZoneName, so name the parts.
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(iso));
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(iso));
}

export const REASON_LABELS: Record<ReturnReason, string> = {
  damaged: "Arrived damaged",
  defective: "Defective / stopped working",
  wrong_item: "Wrong item sent",
  not_as_described: "Not as described",
  changed_mind: "Changed my mind",
};

/** Reasons that need a photo (policy P4). */
export const PHOTO_REASONS: ReturnReason[] = ["damaged", "defective", "wrong_item", "not_as_described"];

// --- Chat (M9) ----------------------------------------------------------------

export type ChatMessage = components["schemas"]["MessageOut"];
export type MessageSender = ChatMessage["sender"];

/** Base labels; ChatThread shows "You" for the viewer's own role instead. */
export const MESSAGE_SENDER_LABELS: Record<MessageSender, string> = {
  customer: "Customer",
  reviewer: "Reviewer",
  bot: "ReturnGuard Assistant",
};

// --- Reviewer ---------------------------------------------------------------

export type QueueItem = components["schemas"]["QueueItem"];
export type ReviewCase = components["schemas"]["CaseOut"];
export type Decision = NonNullable<QueueItem["ai_proposal"]>;
export type EscalationReason = NonNullable<QueueItem["escalation_reason"]>;
export type EvidenceStrength = NonNullable<QueueItem["evidence_strength"]>;
export type OverrideReason = NonNullable<components["schemas"]["DecisionIn"]["override_reason"]>;

/** "Why here": the gate's named reasons, in plain words (DESIGN_SPEC.md 5.3). */
export const ESCALATION_LABELS: Record<EscalationReason, string> = {
  pipeline_error: "Automatic checks failed",
  proposed_denial: "Proposed denial",
  ambiguous_call: "Ambiguous call",
  unverified_photo: "Unverified photo",
  critic_concern: "Re-check raised a concern",
  high_value: "High value",
  elevated_risk: "Elevated risk",
  automation_off: "Automation off",
  qa_sample: "Quality check sample",
  customer_requested_review: "Customer requested review",
};

/** What the reviewer should focus on first, shown in the case banner. */
export const ESCALATION_HINTS: Record<EscalationReason, string> = {
  pipeline_error: "The automatic checks didn't finish. Check everything yourself.",
  proposed_denial: "The checks point to a denial. Only a person can deny a return.",
  ambiguous_call: "The policy hinges on judgment here (for example wear vs. defect).",
  unverified_photo: "The photo hasn't been verified as genuine and matching. Look at it closely.",
  critic_concern: "An independent re-check disagreed with the recommendation.",
  high_value: "Refunds above the high-value limit always need a person (P7).",
  elevated_risk: "The account's return behaviour is above the risk limit.",
  automation_off: "Automatic approvals are switched off, so every case comes to a person.",
  qa_sample: "A clear case picked at random so we can check the AI's work.",
  customer_requested_review: "The customer asked for a second look at a denial.",
};

export const DECISION_LABELS: Record<Decision, string> = {
  approve: "Approve",
  deny: "Deny",
  escalate: "Needs a person",
};

export const STRENGTH_LABELS: Record<EvidenceStrength, string> = {
  strong: "Strong",
  mixed: "Mixed",
  weak: "Weak",
};

export const OVERRIDE_LABELS: Record<OverrideReason, string> = {
  looks_like_defect: "Looks like a defect",
  looks_like_wear: "Looks like wear",
  photo_unclear: "Photo unclear",
  photo_not_genuine: "Photo doesn't look genuine",
  policy_misapplied: "Policy applied wrongly",
  history_explains: "History explains it",
  other: "Other…",
};

/** Audit-log actions in plain words (case history and the admin audit log). */
export const ACTION_LABELS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.logout": "Signed out",
  "auth.signup": "Created an account",
  "order.placed": "Placed an order",
  "seed.loaded": "Demo data loaded",
  "return.submitted": "Customer submitted the return",
  "return.photo_added": "Customer added a photo",
  "return.review_requested": "Customer requested a review",
  "check.missing_evidence": "Data check asked the customer for missing evidence",
  "gate.escalated": "Governance gate sent the case to a person",
  "gate.auto_approved": "Governance gate approved automatically",
  "pipeline.failed": "Automatic checks failed; sent to a person",
  "review.claimed": "Reviewer claimed the case",
  "review.released": "Reviewer released the case",
  "review.approved": "Reviewer approved",
  "review.denied": "Reviewer denied",
  "admin.settings_changed": "Admin changed automation settings",
};

// --- Admin --------------------------------------------------------------------

export type AdminSettings = components["schemas"]["SettingsOut"];
export type AdminMetrics = components["schemas"]["MetricsOut"];
export type AuditEntry = components["schemas"]["AuditEntryOut"];
export type ActorType = AuditEntry["actor_type"];

export const ACTOR_LABELS: Record<ActorType, string> = {
  system: "System",
  check: "Data check",
  ai: "AI",
  gate: "Gate",
  customer: "Customer",
  reviewer: "Reviewer",
  admin: "Admin",
};

export const CATEGORY_LABELS: Record<QueueItem["product_category"], string> = {
  footwear: "Footwear",
  clothing: "Clothing",
  electronics: "Electronics",
  home: "Home",
};

export const STATUS_LABELS: Record<ReturnStatus, string> = {
  needs_info: "We need more information",
  submitted: "Submitted",
  checking: "Being checked",
  under_review: "Under review",
  approved: "Approved",
  denied: "Not approved",
  failed: "Under review",
};
