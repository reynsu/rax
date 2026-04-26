import { useState } from "react";
import { z } from "zod";

const Email = z.string().email();

export function InviteForm({ onInvite }: { onInvite: (email: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const onSubmit = async () => {
    const parsed = Email.safeParse(email);
    if (!parsed.success) { setError("Use a valid email like name@company.com"); return; }
    if (!confirm(`Invite ${parsed.data}?`)) return;
    await onInvite(parsed.data);
  };
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <label>Email <input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      {error && <p role="alert">{error}</p>}
      <button>Send invite</button>
    </form>
  );
}
