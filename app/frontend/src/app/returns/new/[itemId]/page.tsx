import { Suspense } from "react";

import { StartReturnForm } from "./start-return-form";

// The form reads the item id from the URL, which is only known at request time.
export default function StartReturnPage() {
  return (
    <Suspense fallback={<p className="text-zinc-500">Loading…</p>}>
      <StartReturnForm />
    </Suspense>
  );
}
