type Item = { id: string; label: string };
const x: Item = { id: "1", label: "x" };

// ruleid: rax.rel.random-key
const Bad = <li key={Math.random()}>{x.label}</li>;

// ok: rax.rel.random-key
const Good = <li key={x.id}>{x.label}</li>;

export { Bad, Good };
