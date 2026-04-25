import { useState } from "react";

export function CheckoutForm() {
  const [cart, setCart] = useState<string[]>([]);
  // refresh = empty cart, no draft, no saved progress
  return <button onClick={() => setCart([])}>Reset</button>;
}
