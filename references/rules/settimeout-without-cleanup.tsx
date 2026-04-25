import { useEffect, useState } from "react";

export function Bad() {
  const [, setReady] = useState(false);
  useEffect(() => {
    // ruleid: rax.rel.settimeout-without-cleanup
    const t = setTimeout(() => setReady(true), 1500);
    return undefined;
  }, []);
  return null;
}

export function Good() {
  const [, setReady] = useState(false);
  useEffect(() => {
    // ok: rax.rel.settimeout-without-cleanup
    const t = setTimeout(() => setReady(true), 1500);
    return () => { clearTimeout(t); };
  }, []);
  return null;
}
