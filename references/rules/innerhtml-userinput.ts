export function bad(el: HTMLElement, comment: string) {
  // ruleid: rax.sec.innerhtml-userinput
  el.innerHTML = comment;
}

export function good(el: HTMLElement, comment: string) {
  // ok: rax.sec.innerhtml-userinput
  el.textContent = comment;
}
