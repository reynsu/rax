import { v4 as uuid } from "uuid";

export async function transfer(amount: number) {
  const txId = uuid();
  const res = await fetch("/transfers", {
    method: "POST",
    headers: { "Idempotency-Key": txId, "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) throw new Error("transfer failed; backend will compensate via tx id " + txId);
  return await res.json();
}
