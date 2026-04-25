import { ScrollView, FlatList, Text } from "react-native";

type Item = { id: string; label: string };

export function Bad({ items }: { items: Item[] }) {
  // ruleid: rax.perf.scrollview-on-flatlist
  return <ScrollView><FlatList data={items} renderItem={({ item }) => <Text>{item.label}</Text>} keyExtractor={(i) => i.id} /></ScrollView>;
}

export function Good({ items }: { items: Item[] }) {
  // ok: rax.perf.scrollview-on-flatlist
  return <FlatList data={items} renderItem={({ item }) => <Text>{item.label}</Text>} keyExtractor={(i) => i.id} ListHeaderComponent={<Text>Header</Text>} />;
}
