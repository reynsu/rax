export function Order({ data }: { data: any }) {
  // @ts-ignore
  const total = data.items.reduce((a, i) => a + i.price, 0);
  return <p>Total: ${total}</p>;
}
