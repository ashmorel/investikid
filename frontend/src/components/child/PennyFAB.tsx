import { useNavigate } from 'react-router-dom';
import { Penny } from '@/components/child/ui/Penny';

type Props = {
  dueCount: number;
};

export function PennyFAB({ dueCount }: Props) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/coach')}
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
    </button>
  );
}
