import { lazy, Suspense } from "react";
import { FixedSizeList } from "react-window";

const HeavyEditor = lazy(() => import("./HeavyEditor"));

export function App({ items }: { items: string[] }) {
  return (
    <>
      <Suspense fallback={null}><HeavyEditor /></Suspense>
      <FixedSizeList itemCount={items.length} itemSize={32} height={400} width={"100%"}>
        {({ index, style }) => <div style={style}>{items[index]}</div>}
      </FixedSizeList>
    </>
  );
}
