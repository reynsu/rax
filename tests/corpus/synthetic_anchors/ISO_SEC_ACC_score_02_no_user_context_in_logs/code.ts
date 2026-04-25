export async function placeOrder(items: unknown[]) {
  try {
    return await fetch("/orders", { method: "POST", body: JSON.stringify(items) });
  } catch (e) {
    console.log("order failed", e);
  }
}
