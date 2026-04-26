// src/features/checkout/index.ts (public API)
export { CheckoutScreen } from "./screens/CheckoutScreen";
export type { CheckoutState } from "./types";
// internals (./hooks/, ./services/) are NOT re-exported.

// elsewhere:
import { CheckoutScreen, CheckoutState } from "@/features/checkout";
// importing from "@/features/checkout/services/..." is a lint error.
