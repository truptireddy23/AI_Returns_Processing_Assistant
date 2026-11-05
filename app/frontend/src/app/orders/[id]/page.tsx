import { Suspense } from "react";

import { OrderDetailView } from "./order-detail";

// The order id comes from the URL, which is only known at request time.
export default function OrderDetailPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <OrderDetailView />
    </Suspense>
  );
}
