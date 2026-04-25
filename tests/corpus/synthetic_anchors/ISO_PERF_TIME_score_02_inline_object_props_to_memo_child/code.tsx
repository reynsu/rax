import { memo } from "react";

const Heavy = memo(function Heavy({ config }: { config: { theme: string } }) {
  // expensive render
  return <div>{config.theme}</div>;
});

export function Parent() {
  return <Heavy config={{ theme: "dark" }} />;   // new object every render
}
