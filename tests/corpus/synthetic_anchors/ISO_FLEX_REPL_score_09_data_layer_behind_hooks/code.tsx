// data/index.ts — single seam over the storage backend.
export interface PostsRepo { list(): Promise<{ id: string; title: string }[]> }

// data/firebase.ts (impl)
// data/postgrest.ts (alt impl)
// data/mock.ts (test impl)

// hook
import { useQuery } from "@tanstack/react-query";
import { repo } from "./data";   // chosen at app bootstrap

export function usePosts() {
  return useQuery({ queryKey: ["posts"], queryFn: () => repo.list() });
}
