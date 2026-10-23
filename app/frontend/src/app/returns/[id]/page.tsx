import { Suspense } from "react";

import { ReturnStatusView } from "./return-status";

// The return id comes from the URL, which is only known at request time.
export default function ReturnStatusPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <ReturnStatusView />
    </Suspense>
  );
}
