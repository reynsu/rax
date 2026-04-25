import { ErrorBoundary } from "react-error-boundary";
import * as Sentry from "@sentry/react";

function Fallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <section role="alert">
      <p>This area is having trouble: {error.message}</p>
      <button onClick={resetErrorBoundary}>Try again</button>
    </section>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary FallbackComponent={Fallback}
      onError={(e, info) => Sentry.captureException(e, { extra: info })}>
      {children}
    </ErrorBoundary>
  );
}
