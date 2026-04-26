export function ProductCard({ p }: { p: { id: string; title: string; price: number } }) {
  return <article><h2>{p.title}</h2><p>${p.price}</p></article>;
}
export function OrderCard({ o }: { o: { id: string; title: string; total: number } }) {
  return <article><h2>{o.title}</h2><p>${o.total}</p></article>;
}
export function ReviewCard({ r }: { r: { id: string; title: string; rating: number } }) {
  return <article><h2>{r.title}</h2><p>${r.rating}</p></article>;
}
