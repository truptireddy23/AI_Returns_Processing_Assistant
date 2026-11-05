import { Suspense } from "react";

import { CaseView } from "./case-view";

// The case id comes from the URL, which is only known at request time.
export default function ReviewCasePage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <CaseView />
    </Suspense>
  );
}
