"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";

/** productId -> quantity. Prices are never kept here: the server prices the order. */
type Lines = Record<string, number>;

type CartContextValue = {
  lines: Lines;
  count: number;
  add: (productId: string) => void;
  setQuantity: (productId: string, quantity: number) => void;
  clear: () => void;
};

export const MAX_QUANTITY = 5;
const STORAGE_KEY = "returnguard.cart.v1";

const CartContext = createContext<CartContextValue | null>(null);

function load(): Lines {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}");
    if (!parsed || typeof parsed !== "object") return {};
    return Object.fromEntries(
      Object.entries(parsed).filter(
        (e): e is [string, number] => typeof e[1] === "number" && e[1] > 0 && e[1] <= MAX_QUANTITY,
      ),
    );
  } catch {
    return {}; // storage blocked or corrupt: start empty
  }
}

// A tiny external store over localStorage: one snapshot shared by every
// component, kept in sync across tabs through the "storage" event.
const EMPTY: Lines = {};
let snapshot: Lines | null = null;
const listeners = new Set<() => void>();

function read(): Lines {
  snapshot ??= load();
  return snapshot;
}

function write(next: Lines) {
  snapshot = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable: the cart still works for this visit */
  }
  listeners.forEach((notify) => notify());
}

function subscribe(notify: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      snapshot = load();
      notify();
    }
  };
  listeners.add(notify);
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(notify);
    window.removeEventListener("storage", onStorage);
  };
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  // A per-browser convenience only; the cart is rebuilt and repriced at checkout.
  const lines = useSyncExternalStore(subscribe, read, () => EMPTY);
  const setLines = useCallback((update: (l: Lines) => Lines) => write(update(read())), []);

  const add = useCallback(
    (id: string) => setLines((l) => ({ ...l, [id]: Math.min(MAX_QUANTITY, (l[id] ?? 0) + 1) })),
    [setLines],
  );
  const setQuantity = useCallback((id: string, quantity: number) => {
    setLines((l) => {
      const next = { ...l };
      if (quantity <= 0) delete next[id];
      else next[id] = Math.min(MAX_QUANTITY, quantity);
      return next;
    });
  }, [setLines]);
  const clear = useCallback(() => setLines(() => ({})), [setLines]);

  const value = useMemo(
    () => ({ lines, count: Object.values(lines).reduce((a, b) => a + b, 0), add, setQuantity, clear }),
    [lines, add, setQuantity, clear],
  );
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used inside <CartProvider>");
  return ctx;
}
