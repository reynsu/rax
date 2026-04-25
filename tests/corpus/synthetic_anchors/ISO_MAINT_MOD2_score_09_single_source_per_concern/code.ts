import { useQuery } from "@tanstack/react-query";

export function useCurrentUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => fetch("/me").then(r => r.json()),
    staleTime: 60_000,
  });
}

// every consumer reads from useCurrentUser(); no other source of truth.
