type User = { id: string; name: string };
declare const raw: unknown;

// ruleid: rax.rel.unsafe-as-any
const a = raw as any;

// ruleid: rax.rel.unsafe-as-any
const b = raw as unknown as User;

// ok: rax.rel.unsafe-as-any
const c: User = { id: "1", name: "z" };

export { a, b, c };
