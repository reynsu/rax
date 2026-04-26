declare const https: { Agent: new (opts: object) => unknown };
declare function fetch(url: string, opts: object): Promise<unknown>;

export function bad() {
  // ruleid: rax.sec.reject-unauthorized-false
  return new https.Agent({ rejectUnauthorized: false });
}

export function bad2() {
  // ruleid: rax.sec.reject-unauthorized-false
  return fetch("https://api", { rejectUnauthorized: false });
}

export function good() {
  // ok: rax.sec.reject-unauthorized-false
  return new https.Agent({ rejectUnauthorized: true });
}
