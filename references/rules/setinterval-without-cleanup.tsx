import { useEffect, useState } from "react";

export function Bad() {
  const [, setTick] = useState(0);
  useEffect(() => {
    // ruleid: rax.rel.setinterval-without-cleanup
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return undefined;
  }, []);
  return null;
}

export function Good() {
  const [, setTick] = useState(0);
  useEffect(() => {
    // ok: rax.rel.setinterval-without-cleanup
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => { clearInterval(t); };
  }, []);
  return null;
}
