export function makeToken() {
  // ruleid: rax.sec.math-random-for-token
  const token = Math.random();
  return token.toString(36);
}

export function dieRoll() {
  // ok: rax.sec.math-random-for-token
  const score = Math.random();
  return Math.floor(score * 6) + 1;
}
