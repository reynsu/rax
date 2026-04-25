export function Bad({ html }: { html: string }) {
  // ruleid: rax.sec.dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

export function Good({ html }: { html: string }) {
  // ok: rax.sec.dangerously-set-inner-html
  return <div>{html}</div>;
}
