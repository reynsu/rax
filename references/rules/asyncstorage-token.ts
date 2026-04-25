declare const AsyncStorage: { setItem: (k: string, v: string) => Promise<void> };
declare const Keychain: { setGenericPassword: (u: string, p: string) => Promise<void> };

export async function bad(token: string) {
  // ruleid: rax.sec.asyncstorage-token
  await AsyncStorage.setItem("authToken", token);
}

export async function bad2(token: string) {
  // ruleid: rax.sec.asyncstorage-token
  localStorage.setItem("session_jwt", token);
}

export async function good(user: string, token: string) {
  // ok: rax.sec.asyncstorage-token
  await Keychain.setGenericPassword(user, token);
}

export async function ok_for_pref() {
  // ok: rax.sec.asyncstorage-token
  await AsyncStorage.setItem("preferred_theme", "dark");
}
