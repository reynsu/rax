import { useState, useEffect } from "react";

export function Bad({ flag }: { flag: boolean }) {
  if (flag) {
    const [x, setX] = useState(0);  // conditional hook
    useEffect(() => { setX(1); });
    return <p>{x}</p>;
  }
  return null;
}
