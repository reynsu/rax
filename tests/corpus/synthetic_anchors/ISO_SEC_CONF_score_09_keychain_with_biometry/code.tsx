import * as Keychain from "react-native-keychain";

export async function saveToken(user: string, token: string) {
  await Keychain.setGenericPassword(user, token, {
    service: "com.acme.auth",
    accessible: Keychain.ACCESSIBLE.WHEN_PASSCODE_SET_THIS_DEVICE_ONLY,
    accessControl: Keychain.ACCESS_CONTROL.BIOMETRY_CURRENT_SET,
  });
}

export async function loadToken(): Promise<string | null> {
  const creds = await Keychain.getGenericPassword({ service: "com.acme.auth" });
  return creds ? creds.password : null;
}
