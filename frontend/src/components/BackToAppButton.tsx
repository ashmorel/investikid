import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

/**
 * Shared "Back to App" control for the out-of-app areas (admin + parent).
 * One consistent style, target (/home) and copy so it looks and behaves the
 * same everywhere — previously each area rolled its own (a bottom-of-sidebar
 * text link in admin vs a top-header button in parent), which read as
 * inconsistent. Placement within the chrome is controlled by the caller via
 * `className`; the visual treatment stays identical.
 */
export function BackToAppButton({ className }: { className?: string }) {
  const { t } = useTranslation('common');
  return (
    <Link
      to="/home"
      className={cn(
        'inline-flex min-h-[44px] items-center whitespace-nowrap rounded-md px-3 py-1.5',
        'text-sm font-medium text-muted-foreground transition-colors hover:bg-brand-50 hover:text-ink',
        className,
      )}
    >
      {t('backToApp')}
    </Link>
  );
}
