import { cn } from '@/lib/utils';

export type OptionState = 'default' | 'selected' | 'correct' | 'incorrect';

type Props = {
  letter: string;
  state?: OptionState;
  disabled?: boolean;
  onSelect?: () => void;
  children: React.ReactNode;
};

export function OptionCard({ letter, state = 'default', disabled, onSelect, children }: Props) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={state === 'selected' || state === 'correct'}
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'flex w-full items-center gap-3 rounded-2xl border-2 p-3.5 text-left transition-all active:scale-[0.99] disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500',
        state === 'default' && 'border-gray-200 bg-white',
        state === 'selected' && 'border-amber-400 bg-amber-50 shadow-md shadow-orange-500/15',
        state === 'correct' && 'border-green-500 bg-green-50',
        state === 'incorrect' && 'border-red-500 bg-red-50',
      )}
    >
      <span
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm font-extrabold',
          state === 'selected' && 'bg-gradient-to-br from-amber-400 to-orange-500 text-white',
          state === 'correct' && 'bg-green-500 text-white',
          state === 'incorrect' && 'bg-red-500 text-white',
          state === 'default' && 'bg-gray-100 text-gray-500',
        )}
        aria-hidden="true"
      >
        {letter}
      </span>
      <span className="flex-1 text-sm font-bold leading-snug text-gray-900">{children}</span>
    </button>
  );
}
