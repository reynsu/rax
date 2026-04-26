import { useEffect, useState } from "react";

export function App() {
  const [data, setData] = useState<any>();
  useEffect(() => {
    fetch("/api/profile").then(r => r.json()).then(setData);
  }, []);
  return <h1>{data.name}</h1>;   // crashes on first render — no boundary
}
