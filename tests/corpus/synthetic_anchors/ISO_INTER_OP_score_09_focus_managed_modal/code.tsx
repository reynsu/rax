import * as Dialog from "@radix-ui/react-dialog";

export function ConfirmDialog({ open, onConfirm, onClose }: { open: boolean; onConfirm: () => void; onClose: () => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay />
        <Dialog.Content aria-labelledby="confirm-title">
          <Dialog.Title id="confirm-title">Delete this account?</Dialog.Title>
          <Dialog.Description>This cannot be undone.</Dialog.Description>
          <Dialog.Close asChild><button onClick={onConfirm}>Delete</button></Dialog.Close>
          <Dialog.Close asChild><button>Cancel</button></Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
