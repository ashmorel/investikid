import { useTranslation } from 'react-i18next';
import { useOnline } from '@/hooks/useOnline';

/** Local "as of" string: time only if today, else "Mon D, time". */
export function formatAsOf(updatedAt: number, now: Date = new Date()): string {
  const d = new Date(updatedAt);
  const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  if (d.toDateString() === now.toDateString()) return time;
  return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${time}`;
}

/** Freshness caveat shown ONLY while offline and only when data exists. */
export function StaleAsOf({ updatedAt, className }: { updatedAt: number; className?: string }) {
  const online = useOnline();
  const { t } = useTranslation('simulator');
  if (online || !updatedAt) return null;
  return (
    <p className={className ?? 'text-xs text-muted-foreground'}>
      {t('pricesAsOf', { time: formatAsOf(updatedAt) })}
    </p>
  );
}
