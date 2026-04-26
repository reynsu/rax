type User = { id: string; name: string; email: string };
// Backend renamed `name` to `displayName` last sprint.
// This file still has `name`. Runtime returns undefined silently.
export async function loadMe(): Promise<User> {
  return fetch("/me").then(r => r.json());
}
