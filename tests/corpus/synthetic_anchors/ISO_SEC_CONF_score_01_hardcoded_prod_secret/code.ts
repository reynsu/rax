const STRIPE_SECRET = "EXAMPLE_FAKE_PROD_SECRET_PLACEHOLDER_xxxxxxxxxxxx";
export async function charge(amount: number) {
  return fetch("https://api.stripe.com/v1/charges", {
    method: "POST",
    headers: { Authorization: `Bearer ${STRIPE_SECRET}` },
    body: new URLSearchParams({ amount: String(amount) }),
  });
}
