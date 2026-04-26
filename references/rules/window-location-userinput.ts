declare const window: { location: { href: string; assign: (s: string) => void } };

export function bad(redirect: string) {
  // ruleid: rax.sec.window-location-userinput
  window.location.href = redirect;
}

export function bad2(redirect: string) {
  // ruleid: rax.sec.window-location-userinput
  window.location.assign(redirect);
}
