import { View, Text, StyleSheet } from "react-native";

const styles = StyleSheet.create({ box: { padding: 8 } });

export function Bad() {
  // ruleid: rax.perf.inline-rn-style
  return <View style={{ padding: 8 }}><Text>Hi</Text></View>;
}

export function Good() {
  // ok: rax.perf.inline-rn-style
  return <View style={styles.box}><Text>Hi</Text></View>;
}
