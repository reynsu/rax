export async function bad() {
  // ruleid: rax.sec.http-url-in-fetch
  return fetch("http://api.example.com/users");
}

export async function good() {
  // ok: rax.sec.http-url-in-fetch
  return fetch("https://api.example.com/users");
}

export async function devOk() {
  // ok: rax.sec.http-url-in-fetch
  return fetch("http://localhost:3000/health");
}
