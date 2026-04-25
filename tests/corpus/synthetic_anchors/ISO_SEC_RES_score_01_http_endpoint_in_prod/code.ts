export async function getOrders() {
  return fetch("http://api.acme.com/orders").then(r => r.json());
}
