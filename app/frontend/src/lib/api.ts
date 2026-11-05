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

export const STATUS_LABELS: Record<ReturnStatus, string> = {
  needs_info: "We need more information",
  submitted: "Submitted",
  checking: "Being checked",
  under_review: "Under review",
  approved: "Approved",
  denied: "Not approved",
  failed: "Under review",
};
