import { cn } from '@/lib/utils';

export function ErrorBanner({
  title, message, action, className,
}: {
  title: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        'rounded-md border border-destructive/50 bg-destructive/5 p-4 text-destructive',
        className,
      )}
    >
      <h2 className="text-base font-semibold">{title}</h2>
      {message && <p className="mt-1 text-sm">{message}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
