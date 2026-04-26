type ApiError = { code: "rate_limited" | "invalid_email" | "server"; message: string; ref?: string };

export function ResetPasswordError({ err, onRetry }: { err: ApiError; onRetry: () => void }) {
  if (err.code === "rate_limited") return <p>Too many tries. Wait 5 minutes, then <button onClick={onRetry}>retry</button>.</p>;
  if (err.code === "invalid_email") return <p>That email is not registered. <a href="/signup">Create an account</a>.</p>;
  return <p>Something went wrong (ref {err.ref}). <a href="/support">Contact support</a>.</p>;
}
