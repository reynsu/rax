export function bad(expr: string) {
  // ruleid: rax.sec.eval-on-input
  return eval(expr);
}

export function bad2(src: string) {
  // ruleid: rax.sec.eval-on-input
  const fn = new Function("a", "b", src);
  return fn(1, 2);
}

export function good(expr: string) {
  // ok: rax.sec.eval-on-input
  return Number.parseInt(expr, 10);
}
