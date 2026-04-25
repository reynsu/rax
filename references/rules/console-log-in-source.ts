import logger from "./logger";

export function bad(user: { id: string }) {
  // ruleid: rax.maint.console-log-in-source
  console.log("user signed in", user.id);
}

export function good(user: { id: string }) {
  // ok: rax.maint.console-log-in-source
  logger.info({ user_id: user.id }, "user signed in");
}
