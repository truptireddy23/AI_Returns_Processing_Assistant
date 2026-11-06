"use client";

import { useEffect, useRef, useState } from "react";

import {
  api,
  errorMessage,
  formatDateTime,
  MESSAGE_SENDER_LABELS,
  type ChatMessage,
  type ReturnStatus,
} from "@/lib/api";

const POLL_MS = 4000;
const MAX_LENGTH = 2000;

/** What the chat quick-reply chips need to know about the return, kept to the
 * three fields that actually change which questions make sense. */
export type ChatContext = {
  status: ReturnStatus;
  can_request_review: boolean;
};

const ALWAYS = "What's your return policy?";

/** Quick-reply chips for the customer's composer — one tap sends the question,
 * no typing needed. Chosen from the return's own status (and whether a reviewer
 * has already taken over the thread) instead of a fixed list, so they stay
 * relevant as the return moves through the pipeline. Reviewers write their own
 * messages, so this doesn't apply there. */
function suggestedQuestions(context: ChatContext | undefined, takenOver: boolean): string[] {
  if (!context) return [ALWAYS];
  switch (context.status) {
    case "needs_info":
      return ["What information do you still need from me?", "Can I add another photo?", ALWAYS];
    case "submitted":
    case "checking":
      return ["What's the status of my return?", "How long will this take?", ALWAYS];
    case "under_review":
      return takenOver
        ? ["Can you give me an update?", "What are you looking into?", ALWAYS]
        : ["What's the status of my return?", "Why was this sent to a reviewer?", ALWAYS];
    case "approved":
      return ["When will I get my refund?", "How was my refund calculated?", ALWAYS];
    case "denied":
      return context.can_request_review
        ? ["Why was my return denied?", "Can I request another review?", ALWAYS]
        : ["Why was my return denied?", ALWAYS];
    case "failed":
      return ["What's the status of my return?", "How long will this take?", ALWAYS];
    default:
      return [ALWAYS];
  }
}

/** The return's chat thread: a customer's questions, answered by the AI assistant
 * until a reviewer sends a message (then the bot stops answering that thread).
 *
 * `floating`: shows a collapsed launcher button (bottom-right) with an unread
 * badge instead of the panel always being open. Used on the customer's return
 * page; the reviewer's case page stays inline since a reviewer is actively
 * working the case and shouldn't have to notice and open a bubble.
 *
 * `bare`: renders just the message list and composer, with no outer border or
 * "Chat" header of its own — for a caller that already wraps it in its own
 * card (the reviewer's case page, matching its other panels). Not used with
 * `floating`, which always needs its own popup frame. */
export function ChatThread({
  returnId,
  as,
  floating = false,
  bare = false,
  context,
}: {
  returnId: string;
  as: "customer" | "reviewer";
  floating?: boolean;
  bare?: boolean;
  /** The return's status, so the customer's quick-reply chips stay relevant. */
  context?: ChatContext;
}) {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [open, setOpen] = useState(!floating);
  const [unread, setUnread] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);
  // Total message count as of the last poll, so a new tick only counts messages
  // that genuinely arrived since then — not the same ones again every 4s.
  const lastTotal = useRef(0);

  async function load(): Promise<ChatMessage[] | null> {
    const { data } =
      as === "customer"
        ? await api.GET("/api/returns/{return_id}/messages", {
            params: { path: { return_id: returnId } },
          })
        : await api.GET("/api/review/cases/{return_id}/messages", {
            params: { path: { return_id: returnId } },
          });
    return data ?? null;
  }

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      const data = await load();
      if (cancelled || !data) return;
      setMessages(data);
      if (data.length > lastTotal.current) {
        const newOnes = data.slice(lastTotal.current).filter((m) => m.sender !== as);
        if (!open && newOnes.length > 0) setUnread((n) => n + newOnes.length);
      }
      lastTotal.current = data.length;
    }
    tick();
    const timer = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` only closes over stable props
  }, [returnId, as, open]);

  // Clears the badge the moment the panel opens — adjusted during render (not
  // an effect) per https://react.dev/learn/you-might-not-need-an-effect.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setUnread(0);
  }

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  async function sendText(body: string) {
    if (!body.trim()) return;
    setSending(true);
    setError(null);
    const { data, error } =
      as === "customer"
        ? await api.POST("/api/returns/{return_id}/messages", {
            params: { path: { return_id: returnId } },
            body: { body: body.trim() },
          })
        : await api.POST("/api/review/cases/{return_id}/messages", {
            params: { path: { return_id: returnId } },
            body: { body: body.trim() },
          });
    setSending(false);
    if (data) {
      setMessages(data);
      setDraft("");
    } else {
      setError(errorMessage(error, "We couldn't send that message."));
    }
  }

  if (floating && !open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed right-5 bottom-5 z-40 flex items-center gap-2 rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-3 text-sm font-medium text-white shadow-lg shadow-indigo-600/25 transition hover:scale-[1.03] hover:shadow-xl"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
          <path d="M2 4.5A2.5 2.5 0 0 1 4.5 2h11A2.5 2.5 0 0 1 18 4.5v7A2.5 2.5 0 0 1 15.5 14H8l-3.5 3.5a.5.5 0 0 1-.85-.35V14h-.15A2.5 2.5 0 0 1 2 11.5v-7Z" />
        </svg>
        Chat
        {unread > 0 ? (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-red-600 text-xs text-white">
            {unread}
          </span>
        ) : null}
      </button>
    );
  }

  const panel = (
    <div
      className={
        floating
          ? "fixed right-5 bottom-5 z-40 flex w-[22rem] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-2xl dark:border-zinc-800 dark:bg-zinc-950"
          : bare
            ? "flex flex-col gap-2"
            : "card flex flex-col gap-2 overflow-hidden"
      }
    >
      {bare ? null : (
        <div className="flex items-center justify-between border-b border-zinc-200 bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-semibold text-white dark:border-zinc-800">
          <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-300" />Chat with us</span>
          {floating ? (
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="rounded-md p-1 text-white/80 hover:bg-white/15 hover:text-white"
            >
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-4 w-4">
                <path strokeLinecap="round" d="M5 5l10 10M15 5L5 15" />
              </svg>
            </button>
          ) : null}
        </div>
      )}

      {messages === null ? (
        <p className={bare ? "text-sm text-zinc-500" : "p-3 text-sm text-zinc-500"}>Loading…</p>
      ) : (
        <>
          <div
            ref={listRef}
            className={
              bare
                ? "flex max-h-80 flex-col gap-3 overflow-y-auto rounded-xl bg-zinc-50 p-4 dark:bg-zinc-950"
                : "flex max-h-80 min-h-40 flex-col gap-3 overflow-y-auto bg-zinc-50/70 px-4 py-3 dark:bg-zinc-950"
            }
          >
            {messages.length === 0 ? (
              <p className="py-4 text-center text-sm text-zinc-500">
                {as === "customer"
                  ? "Ask a question about your return and the assistant will reply here."
                  : "No messages yet."}
              </p>
            ) : (
              messages.map((m) => {
                const mine = m.sender === as;
                return (
                  <div key={m.id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
                    <span className="mb-0.5 text-[11px] text-zinc-500">
                      {m.sender === as ? "You" : MESSAGE_SENDER_LABELS[m.sender]} ·{" "}
                      {formatDateTime(m.created_at)}
                    </span>
                    <p
                      className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap shadow-sm ${
                        mine
                          ? "rounded-br-md bg-indigo-600 text-white"
                          : "rounded-bl-md border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800"
                      }`}
                    >
                      {m.body}
                    </p>
                  </div>
                );
              })
            )}
          </div>

          {as === "customer" ? (
            <div className={bare ? "flex flex-wrap gap-1.5" : "flex flex-wrap gap-1.5 px-4 pt-1"}>
              {suggestedQuestions(
                context,
                messages.some((m) => m.sender === "reviewer"),
              ).map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => sendText(q)}
                  disabled={sending}
                  className="chip px-2.5 py-1 text-xs"
                >
                  {q}
                </button>
              ))}
            </div>
          ) : null}

          <div
            className={
              bare
                ? "flex flex-col gap-1"
                : "flex flex-col gap-1 border-t border-zinc-100 p-3 dark:border-zinc-800"
            }
          >
            {error ? (
              <p role="alert" className="error-text">
                {error}
              </p>
            ) : null}
            <div className="flex gap-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendText(draft);
                  }
                }}
                maxLength={MAX_LENGTH}
                rows={1}
                placeholder={as === "customer" ? "Ask a question…" : "Message the customer…"}
                className="input flex-1 resize-none"
              />
              <button
                type="button"
                onClick={() => sendText(draft)}
                disabled={sending || !draft.trim()}
                className="btn btn-primary"
              >
                Send
              </button>
            </div>
            {as === "reviewer" ? (
              <p className="hint">
                Sending a message hands this thread to you — the assistant stops auto-replying.
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );

  return panel;
}
