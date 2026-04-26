export function Bad() {
  // ruleid: rax.sec.target-blank-without-noopener
  return <a target="_blank" href="https://example.com">link</a>;
}

export function Good() {
  // ok: rax.sec.target-blank-without-noopener
  return <a target="_blank" rel="noopener noreferrer" href="https://example.com">link</a>;
}
