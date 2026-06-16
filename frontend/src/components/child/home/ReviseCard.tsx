import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useRevisableModules } from '@/api/revise';

export function ReviseCard() {
  const { data: modules } = useRevisableModules();
  if (!modules || modules.length === 0) return null;

  const dueWeak = modules.reduce((n, m) => n + m.due_weak_count, 0);
  const headline =
    dueWeak > 0
      ? `${dueWeak} concept${dueWeak === 1 ? '' : 's'} to practice`
      : 'Keep your learning fresh';
  const sub =
    dueWeak > 0
      ? 'A quick 5-question revision keeps your streak going.'
      : 'Revise a few things you’ve learned.';

  return (
    <Link
      to="/revise/session"
      className="mt-4 flex items-center gap-3 rounded-2xl border border-brand-200 bg-brand-50 p-4 shadow-sm transition-colors hover:bg-brand-100 min-h-[44px]"
      aria-label={`Revise: ${headline}`}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-white">
        <Sparkles className="h-5 w-5" aria-hidden="true" />
      </span>
      <span className="flex flex-col">
        <span className="font-semibold text-brand-900">{headline}</span>
        <span className="text-sm text-brand-700">{sub}</span>
      </span>
    </Link>
  );
}
