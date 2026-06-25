import { cn } from '@/lib/utils';

export type OptionState = 'default' | 'selected' | 'correct' | 'incorrect';

type Props = {
  letter: string;
  state?: OptionState;
  checked?: boolean;
  disabled?: boolean;
  onSelect?: () => void;
  children: React.ReactNode;
};

export function OptionCard({ letter, state = 'default', checked, disabled, onSelect, children }: Props) {
  const isChecked = checked ?? state === 'selected';
  return (
    <button
      type="button"
      role="radio"
      aria-checked={isChecked}
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-3 rounded-2xl border-2 p-3.5 text-left transition-all active:scale-[0.99] disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        state === 'default' && 'border-brand-200 bg-card',
        state === 'selected' &&
          'border-brand-600 bg-brand-100 ring-2 ring-brand-500 shadow-md shadow-brand-600/25',
        state === 'correct' && 'border-success-500 bg-success-50',
        state === 'incorrect' && 'border-danger-500 bg-danger-50',
      )}
    >
      <span
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm font-extrabold',
          state === 'selected' && 'bg-brand-500 text-white',
          state === 'correct' && 'bg-success-500 text-white',
          state === 'incorrect' && 'bg-danger-500 text-white',
          state === 'default' && 'bg-muted text-muted-foreground',
        )}
        aria-hidden="true"
      >
        {letter}
      </span>
      <span className="flex-1 text-sm font-bold leading-snug text-ink">{children}</span>
    </button>
  );
}
