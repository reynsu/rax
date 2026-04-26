// src/foo.ts imports from src/bar.ts; bar imports back foo.
// 800-line component handles fetching, business logic, rendering, navigation.
import { helperFromBar } from "./bar";
export function GodComponent() {
  const x = helperFromBar();
  return <div>{x}</div>;
}
