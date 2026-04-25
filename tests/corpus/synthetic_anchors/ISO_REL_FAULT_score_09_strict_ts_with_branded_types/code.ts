type UserId = string & { readonly __brand: "UserId" };
type OrderId = string & { readonly __brand: "OrderId" };

const userId = (s: string): UserId => s as UserId;
const orderId = (s: string): OrderId => s as OrderId;

export function getOrder(uid: UserId, oid: OrderId) {
  return fetch(`/users/${uid}/orders/${oid}`);
}

const u = userId("u_42");
const o = orderId("o_19");
getOrder(u, o);          // ok
// getOrder(o, u);        // compile error — branded types prevent the swap
