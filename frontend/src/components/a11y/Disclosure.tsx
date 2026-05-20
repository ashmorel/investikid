import { useId, useState, type ReactNode } from 'react';

type Props = { label: string; defaultOpen?: boolean; children: ReactNode };

export function Disclosure({ label, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-semibold text-amber-700 underline"
      >
        {label}
      </button>
      <div id={panelId} hidden={!open} className="mt-2 text-sm text-gray-700">
        {children}
      </div>
    </div>
  );
}
