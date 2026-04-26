type Order = { id: string; placedAt: number; total: number };

export function ordersPlacedAfter(orders: ReadonlyArray<Order>, cutoff: number, newestFirst = true): Order[] {
  const filtered = orders.filter(o => o.placedAt > cutoff);
  return newestFirst ? [...filtered].sort((a, b) => b.placedAt - a.placedAt) : filtered;
}
