export function Bad() {
  // ruleid: rax.a11y.img-without-alt
  return <img src="/banner.png" />;
}

export function Good() {
  // ok: rax.a11y.img-without-alt
  return <img src="/banner.png" alt="Welcome" />;
}

export function Decorative() {
  // ok: rax.a11y.img-without-alt
  return <img src="/sparkle.png" role="presentation" />;
}
