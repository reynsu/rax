import { firestore } from "firebase/firestore";

export function Home() {
  // Component talks to Firebase directly. Migrating off Firebase later
  // touches every component.
  return <div>{firestore?.toString()}</div>;
}
