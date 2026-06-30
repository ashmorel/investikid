import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useRecheckStatus } from '@/api/diagnostic';
import { useAgeTier } from '@/lib/ageTier';

/**
 * Non-blocking Home card that surfaces a progress-check nudge when the backend
 * marks one as due. Completely self-hiding on loading / error / due:false.
 * Dismissible for the session via local state (never gates the app).
 */
export default function ProgressCheckCard() {
  const { t } = useTranslation('diagnostic');
  const { data, isLoading, isError } = useRecheckStatus();
  const tier = useAgeTier();
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState(false);

  // Self-hide on any non-due state
  if (isLoading || isError || !data?.due || dismissed) return null;

  const bodyKey =
    tier === 'investor'
      ? 'progressCheck.cardBody_investor'
      : 'progressCheck.cardBody_explorer';

  return (
    <section
      aria-label={t('progressCheck.cardAriaLabel')}
      className="mb-4 rounded-2xl border border-brand-200 bg-brand-50 px-4 py-3"
    >
      <p className="text-sm font-semibold text-brand-800">{t('progressCheck.cardTitle')}</p>
      <p className="mb-3 text-sm text-brand-700">{t(bodyKey)}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => navigate('/progress-check')}
          className="min-h-[44px] rounded-xl bg-brand-gradient px-4 py-2 text-sm font-bold text-white hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          {t('progressCheck.cardCta')}
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="min-h-[44px] rounded-xl border border-brand-200 px-4 py-2 text-sm text-brand-700 hover:bg-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          {t('progressCheck.cardDismiss')}
        </button>
      </div>
    </section>
  );
}
