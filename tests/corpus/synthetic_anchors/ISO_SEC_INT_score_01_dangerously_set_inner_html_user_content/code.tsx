export function Comment({ html }: { html: string }) {
  return <article dangerouslySetInnerHTML={{ __html: html }} />;
}
