import * as Sentry from "@sentry/react";

Sentry.setUser({ id: "u_42", email: "a@b" });
Sentry.setTag("session_id", "s_19");

export async function placeOrder(items: unknown[]) {
  return Sentry.withScope(async scope => {
    scope.setContext("order", { itemCount: items.length });
    return fetch("/orders", {
      method: "POST",
      body: JSON.stringify(items),
      headers: { "x-trace-id": Sentry.getCurrentHub().getScope()?.getSpan()?.toTraceparent() ?? "" },
    });
  });
}
