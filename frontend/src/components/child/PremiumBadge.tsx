export function PremiumBadge({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-700 ${className ?? ''}`}
    >
      <span aria-hidden="true">✨</span> Premium
    </span>
  );
}
