import { memo, useCallback, useMemo } from "react";

const Row = memo(function Row({ item, onPick }: { item: { id: string; name: string }; onPick: (id: string) => void }) {
  return <li onClick={() => onPick(item.id)}>{item.name}</li>;
});

export function List({ items }: { items: { id: string; name: string }[] }) {
  const sorted = useMemo(() => [...items].sort((a, b) => a.name.localeCompare(b.name)), [items]);
  const onPick = useCallback((id: string) => console.log("picked", id), []);
  return <ul>{sorted.map(it => <Row key={it.id} item={it} onPick={onPick} />)}</ul>;
}
