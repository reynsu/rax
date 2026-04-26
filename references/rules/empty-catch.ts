declare const Sentry: { captureException: (e: unknown) => void };
declare function save(x: unknown): Promise<void>;

export async function bad() {
  // ruleid: rax.rel.empty-catch
  try { await save({}); } catch (e) {}
}

export async function bad2() {
  // ruleid: rax.rel.empty-catch
  await save({}).catch(() => {});
}

export async function good() {
  // ok: rax.rel.empty-catch
  try { await save({}); } catch (e) { Sentry.captureException(e); }
}
