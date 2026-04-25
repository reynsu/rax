import { TouchableOpacity, Pressable, View, Text } from "react-native";

export function Bad({ onClose }: { onClose: () => void }) {
  // ruleid: rax.a11y.touchable-without-a11y
  return <TouchableOpacity onPress={onClose}><Text>X</Text></TouchableOpacity>;
}

export function Good({ onClose }: { onClose: () => void }) {
  // ok: rax.a11y.touchable-without-a11y
  return (
    <TouchableOpacity accessibilityLabel="Close dialog" onPress={onClose}>
      <Text>X</Text>
    </TouchableOpacity>
  );
}
