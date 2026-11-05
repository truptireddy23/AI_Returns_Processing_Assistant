"use client";

import { useEffect, useRef, useState } from "react";

import {
  api,
  errorMessage,
  formatDateTime,
  MESSAGE_SENDER_LABELS,
  type ChatMessage,
} from "@/lib/api";

const POLL_MS = 4000;
const MAX_LENGTH = 2000;

/** The return's chat thread: a customer's questions, answered by the AI assistant
 * until a reviewer sends a message (then the bot stops answering that thread). */
export function ChatThread({
  returnId,
  as,
}: {
  returnId: string;
  /** Which side of the thread this view is on — picks the endpoint and whose
   * own messages show as "You". */
  as: "customer" | "reviewer";
}) {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

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
      if (cancelled) return;
      if (data) setMessages(data);
    }
    tick();
    const timer = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` only closes over stable props
  }, [returnId, as]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    setError(null);
    const { data, error } =
      as === "customer"
        ? await api.POST("/api/returns/{return_id}/messages", {
            params: { path: { return_id: returnId } },
            body: { body },
          })
        : await api.POST("/api/review/cases/{return_id}/messages", {
            params: { path: { return_id: returnId } },
            body: { body },
          });
    setSending(false);
    if (data) {
      setMessages(data);
      setDraft("");
    } else {
      setError(errorMessage(error, "We couldn't send that message."));
    }
  }

  if (messages === null) return <p className="text-sm text-zinc-500">Loading…</p>;

  return (
    <div className="flex flex-col gap-2 rounded border border-zinc-200 dark:border-zinc-800">
      <div className="border-b border-zinc-200 px-3 py-2 text-sm font-medium dark:border-zinc-800">
        Chat
      </div>

      <div ref={listRef} className="flex max-h-72 flex-col gap-2 overflow-y-auto px-3 py-2">
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
                <span className="text-xs text-zinc-500">
                  {m.sender === as ? "You" : MESSAGE_SENDER_LABELS[m.sender]} ·{" "}
                  {formatDateTime(m.created_at)}
                </span>
                <p
                  className={`max-w-[85%] rounded-lg px-3 py-1.5 text-sm whitespace-pre-wrap ${
                    mine
                      ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                      : "bg-zinc-100 dark:bg-zinc-800"
                  }`}
                >
                  {m.body}
                </p>
              </div>
            );
          })
        )}
      </div>

      <div className="flex flex-col gap-1 border-t border-zinc-200 p-2 dark:border-zinc-800">
        {error ? (
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
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
                send();
              }
            }}
            maxLength={MAX_LENGTH}
            rows={1}
            placeholder={as === "customer" ? "Ask a question…" : "Message the customer…"}
            className="flex-1 resize-none rounded-md border border-zinc-300 bg-transparent px-2 py-1.5 text-sm dark:border-zinc-700"
          />
          <button
            type="button"
            onClick={send}
            disabled={sending || !draft.trim()}
            className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            Send
          </button>
        </div>
        {as === "reviewer" ? (
          <p className="text-xs text-zinc-500">
            Sending a message hands this thread to you — the assistant stops auto-replying.
          </p>
        ) : null}
      </div>
    </div>
  );
}
