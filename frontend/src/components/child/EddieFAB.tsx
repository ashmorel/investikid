import { useNavigate } from 'react-router-dom';

type Props = {
  dueCount: number;
};

export function EddieFAB({ dueCount }: Props) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/coach')}
      aria-label="Open Coach Eddie"
      className="fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-amber-400 to-orange-500 shadow-lg transition-transform hover:scale-105 active:scale-95"
    >
      <span className="text-2xl" aria-hidden="true">💡</span>
      {dueCount > 0 && (
        <span
          data-testid="eddie-badge"
          className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-red-500"
        />
      )}
    </button>
  );
}
