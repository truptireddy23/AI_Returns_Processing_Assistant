"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireRole } from "@/components/require-role";
import { StatusBadge } from "@/components/status-badge";
import {
  api,
  DECISION_LABELS,
  ESCALATION_REASON_LABELS,
  errorMessage,
  EVIDENCE_LABELS,
  findingRows,
  formatDateTime,
  formatMoney,
  REASON_LABELS,
  STEP_LABELS,
  type CaseDetail,
  type Decision,
  type Finding,
} from "@/lib/api";

export function CaseDetailView() {
  return <RequireRole roles={["reviewer", "admin"]}>{() => <Case />}</RequireRole>;
}

function Case() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.GET("/api/review/{return_id}", { params: { path: { return_id: id } } }).then(
      ({ data, error }) => {
        if (data) {
          setDetail(data);
          setError(null);
        } else {
          setError(errorMessage(error, "We couldn't load this case."));
        }
      },
    );
  }, [id]);

  if (error) return <p role="alert" className="text-red-700">{error}</p>;
  if (!detail) return <p className="text-zinc-500">Loading…</p>;

  const decidable = detail.status === "under_review" || detail.status === "failed";

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Case R-{detail.case_number}</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Order #{detail.order_number} · {formatDateTime(detail.created_at)}
          </p>
        </div>
        <StatusBadge status={detail.status} />
      </div>

      {detail.escalation_reason ? (
        <div
          role="status"
          className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
        >
          <strong>Why here:</strong> {ESCALATION_REASON_LABELS[detail.escalation_reason]}
        </div>
      ) : null}

      {detail.review_request ? (
        <div
          role="status"
          className="rounded border border-violet-300 bg-violet-50 p-3 text-sm text-violet-900"
        >
          <strong>The customer asked for another look:</strong>{" "}
          {detail.review_request.customer_explanation}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2 rounded border border-zinc-200 p-4 dark:border-zinc-800">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <span className="rounded bg-zinc-900 px-1 py-0.5 text-[10px] font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
              AI
            </span>
            Recommendation
          </h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-zinc-500">Proposal</dt>
            <dd>{detail.ai_proposal ? DECISION_LABELS[detail.ai_proposal] : "—"}</dd>
            <dt className="text-zinc-500">Evidence strength</dt>
            <dd>{detail.evidence_strength ? EVIDENCE_LABELS[detail.evidence_strength] : "—"}</dd>
            <dt className="text-zinc-500">Policy version</dt>
            <dd>{detail.policy_version ?? "—"}</dd>
          </dl>
        </div>
        <div className="flex flex-col gap-2 rounded border border-zinc-200 p-4 dark:border-zinc-800">
          <h2 className="text-sm font-semibold">Customer history</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-zinc-500">Account age</dt>
            <dd>{detail.customer_history.account_age_days} days</dd>
            <dt className="text-zinc-500">Past orders</dt>
            <dd>{detail.customer_history.past_orders}</dd>
            <dt className="text-zinc-500">Past returns</dt>
            <dd>{detail.customer_history.past_returns}</dd>
            <dt className="text-zinc-500">Recent returns (30d)</dt>
            <dd>{detail.customer_history.recent_returns_30d}</dd>
            <dt className="text-zinc-500">Other accounts, same address</dt>
            <dd>{detail.customer_history.other_accounts_at_address}</dd>
          </dl>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold">Item</h2>
        <p className="text-sm">
          {detail.product_name} · {formatMoney(detail.refund_amount_cents)} ·{" "}
          {REASON_LABELS[detail.reason]}
        </p>
        {detail.reason_text ? (
          <p className="whitespace-pre-wrap text-sm text-zinc-700 dark:text-zinc-300">
            &quot;{detail.reason_text}&quot;
          </p>
        ) : null}
      </div>

      {detail.photos.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold">Photos</h2>
          <div className="flex flex-wrap gap-2">
            {detail.photos.map((p) => (
              // Served only to this return's customer and to staff.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={p.id}
                src={p.url}
                alt="Return photo"
                className="h-40 w-40 rounded border border-zinc-200 object-cover dark:border-zinc-800"
              />
            ))}
          </div>
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">Pipeline findings</h2>
        {detail.findings.map((f) => (
          <FindingCard key={f.step} finding={f} />
        ))}
      </div>

      {decidable ? (
        <DecisionPanel
          returnId={detail.id}
          aiProposal={detail.ai_proposal}
          onDecided={(updated) => setDetail(updated)}
        />
      ) : (
        <div className="rounded border border-zinc-200 p-4 text-sm dark:border-zinc-800">
          Decided: {detail.final_decision ? DECISION_LABELS[detail.final_decision] : "—"}
          {detail.decided_by_type ? ` by a ${detail.decided_by_type}` : ""}
        </div>
      )}

      <Link href="/review" className="text-sm underline">
        Back to queue
      </Link>
    </section>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const rows = findingRows(finding.output);
  return (
    <div className="rounded border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-medium">{STEP_LABELS[finding.step] ?? finding.step}</span>
        {finding.source ? (
          <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] tracking-wide text-zinc-600 uppercase dark:bg-zinc-800 dark:text-zinc-400">
            {finding.source}
          </span>
        ) : null}
        {finding.model ? <span className="text-xs text-zinc-500">{finding.model}</span> : null}
      </div>
      {rows.length > 0 ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
          {rows.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-zinc-500 capitalize">{k}</dt>
              <dd className="break-words">{v}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-zinc-500">No details recorded.</p>
      )}
    </div>
  );
}

function DecisionPanel({
  returnId,
  aiProposal,
  onDecided,
}: {
  returnId: string;
  aiProposal: Decision | null;
  onDecided: (detail: CaseDetail) => void;
}) {
  const [overrideReason, setOverrideReason] = useState("");
  const [confirmingDeny, setConfirmingDeny] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(decision: "approve" | "deny") {
    setBusy(true);
    setError(null);
    const { data, error } = await api.POST("/api/review/{return_id}/decide", {
      params: { path: { return_id: returnId } },
      body: { decision, override_reason: overrideReason.trim() || undefined },
    });
    setBusy(false);
    if (data) {
      onDecided(data);
      setConfirmingDeny(false);
    } else {
      setError(errorMessage(error, "We couldn't save that decision."));
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-sm font-semibold">Your decision</h2>
      {error ? (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      ) : null}
      <label className="flex flex-col gap-1 text-sm">
        Disagree with the AI? Reason (required if you do)
        <input
          type="text"
          value={overrideReason}
          onChange={(e) => setOverrideReason(e.target.value)}
          className="rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
          placeholder={
            aiProposal ? `The AI proposed: ${DECISION_LABELS[aiProposal]}` : "Optional"
          }
        />
      </label>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => submit("approve")}
          className="rounded-md bg-green-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Approve
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => setConfirmingDeny(true)}
          className="rounded-md bg-red-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Deny…
        </button>
      </div>
      {confirmingDeny ? (
        <div
          role="alertdialog"
          aria-label="Confirm denial"
          className="flex flex-col gap-2 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900"
        >
          <p>
            Deny this return? The customer will be told this decision was made by a person, and
            can request a review.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setConfirmingDeny(false)}
              className="rounded border border-zinc-300 px-3 py-1.5"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => submit("deny")}
              className="rounded bg-red-700 px-3 py-1.5 text-white disabled:opacity-50"
            >
              Confirm denial
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
