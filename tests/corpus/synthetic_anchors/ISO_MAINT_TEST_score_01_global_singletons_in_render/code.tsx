import { firebaseDb } from "../firebase";   // shared singleton

export function Home() {
  const docs = (window as any).__seed__ ?? firebaseDb.collection("posts").get();
  return <ul>{(docs?.items ?? []).map((d: any) => <li>{d.title}</li>)}</ul>;
}
