import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLeaderboard } from '@/hooks/useLeaderboard';
import type { LeaderboardScope, LeaderboardMetric } from '@/api/gamification';
import { LeaderboardTable } from './LeaderboardTable';

const SCOPES: LeaderboardScope[] = ['market', 'global', 'friends'];
const METRICS: LeaderboardMetric[] = ['xp', 'arcade'];

export function LeaderboardCard({ currentName }: { currentName: string }) {
  const { t } = useTranslation('child');
  const [scope, setScope] = useState<LeaderboardScope>('market');
  const [metric, setMetric] = useState<LeaderboardMetric>('xp');
  const { data, isLoading, isError } = useLeaderboard(scope, metric);

  return (
    <section aria-labelledby="lb-heading">
      <h2 id="lb-heading" className="mb-3 text-sm font-extrabold uppercase tracking-wider text-gray-700">
        {t('leaderboard.title')}
      </h2>
      <div role="tablist" aria-label={t('leaderboard.scopeLabel')} className="mb-2 flex gap-1 rounded-2xl border border-brand-200 bg-brand-50 p-1">
        {SCOPES.map((s) => (
          <button key={s} role="tab" type="button" aria-selected={scope === s}
            onClick={() => setScope(s)}
            className={`min-h-[44px] flex-1 rounded-xl px-3 text-sm font-bold ${scope === s ? 'bg-white text-brand-800 shadow-sm' : 'text-brand-600'}`}>
            {t(`leaderboard.scope.${s}`)}
          </button>
        ))}
      </div>
      <div role="tablist" aria-label={t('leaderboard.metricLabel')} className="mb-3 flex gap-1">
        {METRICS.map((m) => (
          <button key={m} role="tab" type="button" aria-selected={metric === m}
            onClick={() => setMetric(m)}
            className={`min-h-[36px] rounded-full px-3 text-xs font-bold ${metric === m ? 'bg-brand-600 text-white' : 'bg-brand-100 text-brand-700'}`}>
            {t(`leaderboard.metric.${m}`)}
          </button>
        ))}
      </div>
      {isLoading && <p className="py-6 text-center text-sm text-muted-foreground">{t('leaderboard.loading')}</p>}
      {isError && <p role="alert" className="py-6 text-center text-sm text-red-700">{t('leaderboard.error')}</p>}
      {data && (
        data.length === 0
          ? <p className="py-8 text-center text-muted-foreground">{scope === 'friends' ? t('leaderboard.friendsEmpty') : t('leaderboard.empty')}</p>
          : <LeaderboardTable rows={data} currentName={currentName}
              pointsLabel={metric === 'xp' ? t('leaderboard.colXp') : t('leaderboard.colPoints')} />
      )}
    </section>
  );
}
