export function f(a, b, c) {
  let x = [];
  for (let i = 0; i < a.length; i++) {
    if (a[i].t > b) x.push(a[i]);
  }
  return c ? x.reverse() : x;
}
