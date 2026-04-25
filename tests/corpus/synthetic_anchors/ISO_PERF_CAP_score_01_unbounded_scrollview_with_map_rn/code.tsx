import { ScrollView, Text } from "react-native";
type Msg = { id: string; body: string };
export function Feed({ messages }: { messages: Msg[] }) {
  return <ScrollView>{messages.map(m => <Text key={m.id}>{m.body}</Text>)}</ScrollView>;
}
