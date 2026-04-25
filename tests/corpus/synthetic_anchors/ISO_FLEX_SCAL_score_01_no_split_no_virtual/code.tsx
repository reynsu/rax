import HeavyEditor from "./HeavyEditor"; // 1.2 MB

export function App({ items }: { items: string[] }) {
  return (
    <>
      <HeavyEditor />
      <ul>{items.map(i => <li key={i}>{i}</li>)}</ul>
    </>
  );
}
