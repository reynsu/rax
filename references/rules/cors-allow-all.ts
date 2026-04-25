type Res = { setHeader: (k: string, v: string) => void; headers: Record<string, string> };

export function bad(res: Res) {
  // ruleid: rax.sec.cors-allow-all
  res.setHeader("Access-Control-Allow-Origin", "*");
}

export function good(res: Res, origin: string) {
  const allowed = new Set(["https://my.app", "https://www.my.app"]);
  if (allowed.has(origin)) {
    // ok: rax.sec.cors-allow-all
    res.setHeader("Access-Control-Allow-Origin", origin);
  }
}
