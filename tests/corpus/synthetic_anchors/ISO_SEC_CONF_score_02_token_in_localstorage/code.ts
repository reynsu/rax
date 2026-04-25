import { useEffect } from "react";
export function App() {
  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then(r => r.json())
      .then(({ jwt }) => localStorage.setItem("authToken", jwt));
  }, []);
  return null;
}
