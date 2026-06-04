import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel }: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" role="dialog" aria-label={title}>
      <div className="w-full max-w-sm rounded-lg border border-line bg-card p-6">
        <h3 className="mb-2 text-lg font-semibold text-ink">{title}</h3>
        {message && <p className="mb-4 text-sm text-muted-foreground">{message}</p>}
        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="rounded-md border border-line px-4 py-2 text-sm text-muted-foreground hover:bg-brand-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-danger-600 px-4 py-2 text-sm text-white hover:bg-danger-500"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
