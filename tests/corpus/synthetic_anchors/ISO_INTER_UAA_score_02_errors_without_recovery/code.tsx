export function ResetPassword({ error }: { error: string | null }) {
  if (error) return <p>Error: {error}</p>;   // raw, no next step
  return null;
}
