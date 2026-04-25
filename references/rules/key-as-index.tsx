type Item = { id: string; label: string };

export function Bad({ items }: { items: Item[] }) {
  // ruleid: rax.rel.key-as-index
  return <ul>{items.map((it, i) => <li key={i}>{it.label}</li>)}</ul>;
}

export function Good({ items }: { items: Item[] }) {
  // ok: rax.rel.key-as-index
  return <ul>{items.map((it) => <li key={it.id}>{it.label}</li>)}</ul>;
}
