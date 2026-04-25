import { ScrollView, FlatList, View, Text } from "react-native";

export function Bad({ items }: { items: string[] }) {
  // ruleid: rax.perf.scrollview-with-map
  return <ScrollView>{items.map((it) => <Text key={it}>{it}</Text>)}</ScrollView>;
}

export function Good({ items }: { items: string[] }) {
  // ok: rax.perf.scrollview-with-map
  return <FlatList data={items} renderItem={({ item }) => <Text>{item}</Text>} keyExtractor={(i) => i} />;
}
