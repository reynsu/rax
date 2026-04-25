export function CloseButton({ onClose }: { onClose: () => void }) {
  return <div onClick={onClose} style={{ cursor: "pointer" }}>X</div>;
}
