import { cn } from '@/lib/utils';

const TONE: Record<'ink' | 'success' | 'danger', string> = {
  ink: 'text-ink',
  success: 'text-success-700',
  danger: 'text-danger-700',
};

export function QuickStatCard({
  label,
  value,
  emoji,
  tone = 'ink',
}: {
  label: string;
  value: string;
  emoji?: string;
  tone?: 'ink' | 'success' | 'danger';
}) {
  return (
    <div className="rounded-2xl border border-brand-100 bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold text-muted-foreground">{label}</p>
        {emoji && <span className="text-xl" aria-hidden="true">{emoji}</span>}
      </div>
      <p className={cn('mt-0.5 text-lg font-extrabold', TONE[tone])}>{value}</p>
    </div>
  );
}
