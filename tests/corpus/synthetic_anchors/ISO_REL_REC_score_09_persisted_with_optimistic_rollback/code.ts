import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (next: { name: string }) =>
      fetch("/profile", { method: "PUT", body: JSON.stringify(next) }),
    onMutate: async (next) => {
      await qc.cancelQueries({ queryKey: ["profile"] });
      const prev = qc.getQueryData(["profile"]);
      qc.setQueryData(["profile"], next);
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(["profile"], ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });
}
