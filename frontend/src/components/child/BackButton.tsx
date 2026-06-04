import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

export function BackButton({ to, label, className }: { to: string; label: string; className?: string }) {
  return (
    <Link
      to={to}
      aria-label={`Back to ${label}`}
      className={cn(
        'inline-flex min-h-[44px] items-center gap-1 rounded-lg px-2 py-2 text-base font-semibold text-brand-700 transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400',
        className,
      )}
    >
      <ChevronLeft className="h-5 w-5" aria-hidden="true" />
      <span>{label}</span>
    </Link>
  );
}
