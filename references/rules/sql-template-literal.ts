declare const db: {
  query: (s: string, args?: unknown[]) => Promise<unknown>;
};

export async function bad(userId: string) {
  // ruleid: rax.sec.sql-template-literal
  return db.query(`SELECT id FROM users WHERE id = ${userId}`);
}

export async function good(userId: string) {
  // ok: rax.sec.sql-template-literal
  return db.query("SELECT id FROM users WHERE id = $1", [userId]);
}
