export async function transfer(amount: number) {
  await fetch("/balance/debit", { method: "POST", body: JSON.stringify({ amount }) });
  await fetch("/balance/credit", { method: "POST", body: JSON.stringify({ amount }) });
  // Any error between these two leaves money debited but not credited.
}
