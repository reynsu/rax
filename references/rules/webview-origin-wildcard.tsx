import { WebView } from "react-native-webview";

export function Bad() {
  // ruleid: rax.sec.webview-origin-wildcard
  return <WebView source={{ uri: "https://my.app" }} originWhitelist={["*"]} />;
}

export function Good() {
  // ok: rax.sec.webview-origin-wildcard
  return <WebView source={{ uri: "https://my.app" }} originWhitelist={["https://my.app"]} />;
}
