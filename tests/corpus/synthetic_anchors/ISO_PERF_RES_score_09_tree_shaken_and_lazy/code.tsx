import { format } from "date-fns/format";
import { lazy, Suspense } from "react";

const Charts = lazy(() => import("./Charts"));

export function Dashboard({ d }: { d: Date }) {
  const dedup = (xs: string[]) => Array.from(new Set(xs));
  return (
    <Suspense fallback={null}>
      <p>{format(d, "yyyy-MM-dd")}</p>
      <Charts items={dedup(["a", "b", "a"])} />
    </Suspense>
  );
}
