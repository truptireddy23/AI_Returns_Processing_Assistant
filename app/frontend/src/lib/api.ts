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
export type CaseDetail = components["schemas"]["CaseDetailOut"];
export type Finding = components["schemas"]["FindingOut"];
export type Decision = components["schemas"]["Decision"];
export type EscalationReason = components["schemas"]["EscalationReason"];
export type EvidenceStrength = components["schemas"]["EvidenceStrength"];
export type QueueItem = components["schemas"]["QueueItem"];
export type SettingsOut = components["schemas"]["SettingsOut"];
export type AuditLogEntry = components["schemas"]["AuditLogEntryOut"];

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

export const STATUS_LABELS: Record<ReturnStatus, string> = {
  needs_info: "We need more information",
  submitted: "Submitted",
  checking: "Being checked",
  under_review: "Under review",
  approved: "Approved",
  denied: "Not approved",
  failed: "Under review",
};

export const ESCALATION_REASON_LABELS: Record<EscalationReason, string> = {
  pipeline_error: "The pipeline hit an error",
  proposed_denial: "Proposed denial",
  ambiguous_call: "Ambiguous call",
  unverified_photo: "Unverified photo",
  critic_concern: "Critic flagged a concern",
  high_value: "High value",
  elevated_risk: "Elevated risk",
  automation_off: "Automation is off",
  qa_sample: "QA sample",
  customer_requested_review: "Customer requested review",
};

export const DECISION_LABELS: Record<Decision, string> = {
  approve: "Approve",
  deny: "Deny",
  escalate: "Escalate",
};

export const EVIDENCE_LABELS: Record<EvidenceStrength, string> = {
  strong: "Strong",
  mixed: "Mixed",
  weak: "Weak",
};

export const STEP_LABELS: Record<string, string> = {
  data_check: "Data check",
  policy: "Policy",
  image: "Photo",
  behavior: "Behavior risk",
  recommendation: "Recommendation",
  critic: "Critic",
  gate: "Governance gate",
};

function renderFindingValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length ? v.map(renderFindingValue).join(", ") : "—";
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>);
    return entries.length
      ? entries.map(([k, vv]) => `${k.replace(/_/g, " ")}: ${renderFindingValue(vv)}`).join(", ")
      : "—";
  }
  return String(v);
}

/** Turns a step's raw `output` dict into readable rows, skipping the full raw
 * model response (its individual fields are already shown separately). */
export function findingRows(output: Record<string, unknown>): [string, string][] {
  const skip = new Set(["raw_response"]);
  return Object.entries(output)
    .filter(([k]) => !skip.has(k))
    .map(([k, v]) => [k.replace(/_/g, " "), renderFindingValue(v)]);
}
