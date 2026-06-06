import { Penny } from '@/components/child/ui/Penny';
import { PremiumBadge } from '@/components/child/PremiumBadge';

type Props = {
  dueCount: number;
  onOpen?: () => void;
  locked?: boolean;
};

export function PennyFAB({ dueCount, onOpen, locked = false }: Props) {
  return (
    <button
      onClick={onOpen}
      aria-label="Open Coach Penny"
      className="fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-gradient shadow-lg transition-transform hover:scale-105 active:scale-95"
    >
      <Penny size={34} mood="happy" />
      {dueCount > 0 && (
        <span
          data-testid="penny-badge"
          className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-danger-500"
        />
      )}
      {locked && (
        <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <PremiumBadge />
        </span>
      )}
    </button>
  );
}
