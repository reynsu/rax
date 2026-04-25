import { FlatList, Text } from "react-native";
import { memo } from "react";

const ROW_HEIGHT = 56;
type Msg = { id: string; body: string };

const Row = memo(({ item }: { item: Msg }) => <Text style={{ height: ROW_HEIGHT }}>{item.body}</Text>);

export function Feed({ messages }: { messages: Msg[] }) {
  return (
    <FlatList
      data={messages}
      keyExtractor={(i) => i.id}
      renderItem={({ item }) => <Row item={item} />}
      getItemLayout={(_, index) => ({ length: ROW_HEIGHT, offset: ROW_HEIGHT * index, index })}
      windowSize={7}
      maxToRenderPerBatch={10}
      removeClippedSubviews
    />
  );
}
