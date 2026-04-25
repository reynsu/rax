import type { ReactNode } from "react";

export function Card({ title, children }: { title: ReactNode; children: ReactNode }) {
  return <article><h2>{title}</h2>{children}</article>;
}

// callers
// <Card title={p.title}><p>${p.price}</p></Card>
// <Card title={o.title}><p>${o.total}</p></Card>
