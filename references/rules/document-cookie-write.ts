declare const document: { cookie: string };

export function bad(token: string) {
  // ruleid: rax.sec.document-cookie-write
  document.cookie = `auth=${token}`;
}
