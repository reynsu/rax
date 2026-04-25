import { authClient } from "./auth-client";  // wraps oidc-client-ts

export async function login() {
  await authClient.signinRedirect({
    response_type: "code",
    code_challenge_method: "S256",
    scope: "openid profile email offline_access",
  });
}

export async function callApi(path: string) {
  const user = await authClient.getUser();
  if (!user || user.expired) await authClient.signinSilent();
  const fresh = await authClient.getUser();
  return fetch(path, { headers: { Authorization: `Bearer ${fresh?.access_token}` } });
}
