export function Bad() {
  // ruleid: rax.sec.iframe-without-sandbox
  return <iframe src="https://thirdparty.example.com/widget" />;
}

export function Good() {
  // ok: rax.sec.iframe-without-sandbox
  return <iframe src="https://thirdparty.example.com/widget" sandbox="allow-scripts" />;
}
