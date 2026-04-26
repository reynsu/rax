import { fetch as pinnedFetch } from "react-native-ssl-pinning";

const PINS = ["sha256/abc...=", "sha256/def...="];   // primary + backup

export async function api(path: string, init: RequestInit = {}) {
  return pinnedFetch(`https://api.acme.com${path}`, {
    ...init,
    sslPinning: { certs: PINS, hashes: PINS },
    timeoutInterval: 8,
  });
}
