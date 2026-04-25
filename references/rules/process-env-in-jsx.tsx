export function Bad() {
  // ruleid: rax.sec.process-env-in-jsx
  return <span>{process.env.STRIPE_SECRET_KEY}</span>;
}

export function Good() {
  // ok: rax.sec.process-env-in-jsx
  return <span>{process.env.NEXT_PUBLIC_APP_VERSION}</span>;
}
