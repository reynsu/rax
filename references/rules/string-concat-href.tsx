export function Bad({ host }: { host: string }) {
  // ruleid: rax.sec.string-concat-href
  return <a href={"https://" + host}>open</a>;
}

export function Good({ host }: { host: string }) {
  const url = new URL("/", `https://${host}`);
  // ok: rax.sec.string-concat-href
  return <a href={url.toString()}>open</a>;
}
