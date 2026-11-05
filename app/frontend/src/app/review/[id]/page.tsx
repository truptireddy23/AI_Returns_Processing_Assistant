import { Suspense } from "react";

import { CaseDetailView } from "./case-detail";

// The case id comes from the URL, which is only known at request time.
export default function CaseDetailPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <CaseDetailView />
    </Suspense>
  );
}
