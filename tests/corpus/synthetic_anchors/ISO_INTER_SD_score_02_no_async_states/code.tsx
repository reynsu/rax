import { useEffect, useState } from "react";
export function Inbox() {
  const [msgs, setMsgs] = useState<string[]>([]);
  useEffect(() => { fetch("/inbox").then(r => r.json()).then(setMsgs); }, []);
  return <ul>{msgs.map(m => <li key={m}>{m}</li>)}</ul>;
  // No loading, no empty state, no error state. UI shows blank during fetch.
}
