import { useColorScheme } from "react-native";

const tokens = {
  light: { surface: "#fff", text: "#0b0b0b" },
  dark:  { surface: "#0b0b0b", text: "#f5f5f5" },
};

export function Card({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme();
  const t = tokens[scheme === "dark" ? "dark" : "light"];
  return <article style={{ padding: 16, color: t.text, background: t.surface }}>{children}</article>;
}
