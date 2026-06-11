export function MasteredStamp({ masteredAt, className }: { masteredAt: string; className?: string }) {
  const date = new Date(masteredAt).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-success-100 px-2 py-0.5 text-xs font-semibold text-success-700 ${className ?? ''}`}
    >
      Mastered <span aria-hidden="true">✓</span> {date}
    </span>
  );
}
