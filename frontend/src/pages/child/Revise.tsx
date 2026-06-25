import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useRevisableModules } from '@/api/revise';
import { useTranslation } from 'react-i18next';

export default function Revise() {
  const { t } = useTranslation('revise');
  const { data: modules, isLoading } = useRevisableModules();

  return (
    <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
      <h1 className="text-2xl font-bold">{t('pageTitle')}</h1>
      <Link
        to="/revise/session"
        className="mt-4 flex items-center gap-3 rounded-2xl border border-brand-200 bg-brand-600 p-4 text-white shadow-sm min-h-[44px]"
      >
        <Sparkles className="h-5 w-5" aria-hidden="true" />
        <span className="font-semibold">{t('hub.dailyRevise')}</span>
        <span className="ml-auto text-sm text-brand-100">{t('hub.dailyReviseSubtitle')}</span>
      </Link>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">{t('hub.loading')}</p>
      ) : !modules || modules.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          {t('hub.empty')}
        </p>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {modules.map((m) => (
            <li key={m.module_id}>
              <Link
                to={`/revise/session?module=${m.module_id}`}
                className="flex items-center gap-3 rounded-2xl border border-brand-200 bg-card p-4 shadow-sm transition-colors hover:bg-brand-50 min-h-[44px]"
              >
                <span className="text-2xl" aria-hidden="true">{m.icon}</span>
                <span className="font-semibold">{m.title}</span>
                {m.due_weak_count > 0 ? (
                  <span className="ml-auto rounded-full bg-danger-100 px-2 py-0.5 text-sm font-semibold text-danger-700">
                    {t('hub.dueBadge', { count: m.due_weak_count })}
                  </span>
                ) : (
                  <span className="ml-auto text-sm text-muted-foreground">{t('hub.refreshLabel')}</span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
