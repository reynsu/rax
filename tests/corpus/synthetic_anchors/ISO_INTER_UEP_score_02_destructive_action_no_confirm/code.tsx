import { useMutation } from "@tanstack/react-query";

export function DeleteAllPhotosButton() {
  const m = useMutation({ mutationFn: () => fetch("/photos", { method: "DELETE" }) });
  return <button onClick={() => m.mutate()}>Delete all photos</button>;
}
