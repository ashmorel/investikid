import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAnalyticsSummary } from '@/api/admin';

const RANGES = [7, 30, 90] as const;

function fmtPct(value: number | null): string {
  return value === null ? '—' : `${value}%`;
}

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

export default function AdminAnalytics() {
  const { t } = useTranslation('admin');
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError } = useAnalyticsSummary(days);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t('analytics.pageTitle')}</h1>
        <div role="group" aria-label={t('analytics.dateRangeLabel')} className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setDays(r)}
              aria-pressed={days === r}
              className={`min-h-[36px] rounded-md px-3 py-1.5 text-sm font-semibold ${
                days === r ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 border border-gray-300'
              }`}
            >
              {/* eslint-disable-next-line i18next/no-literal-string */}
              {r}d
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="mt-6 text-sm text-gray-500">{t('analytics.loading')}</p>}
      {isError && (
        <p role="alert" className="mt-6 text-sm font-semibold text-red-700">
          {t('analytics.error')}
        </p>
      )}

      {data && (
        <div className="mt-4 space-y-6">
          <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard
              label={t('analytics.kpi.activation')}
              value={fmtPct(data.activation.rate_pct)}
              sub={t('analytics.kpi.activatedSignups', { activated: data.activation.activated, signups: data.activation.signups })}
            />
            <KpiCard
              label={t('analytics.kpi.heroTapThrough')}
              value={fmtPct(data.engagement.cta_through_pct)}
              sub={t('analytics.kpi.tapsAndViews', { taps: data.engagement.home_cta_tap, views: data.engagement.home_view })}
            />
            <KpiCard
              label={t('analytics.kpi.lessonsCompleted')}
              value={String(data.engagement.lesson_completed)}
              sub={t('analytics.kpi.lastDays', { days: data.window_days })}
            />
            <KpiCard
              label={t('analytics.kpi.digestsSent')}
              value={String(data.engagement.digest_sent)}
              sub={t('analytics.kpi.lastDays', { days: data.window_days })}
            />
          </section>

          <section aria-label={t('analytics.trialFunnel.heading')}>
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">{t('analytics.trialFunnel.heading')}</h2>
            <div className="mt-2 grid grid-cols-3 gap-3">
              <KpiCard label={t('analytics.trialFunnel.paywallViews')} value={String(data.funnel.paywall_view)} />
              <KpiCard label={t('analytics.trialFunnel.trialsStarted')} value={String(data.funnel.trial_started)} sub={t('analytics.trialFunnel.trialsStartedSub')} />
              <KpiCard label={t('analytics.trialFunnel.subscriptions')} value={String(data.funnel.subscription_activated)} />
            </div>
          </section>

          <section aria-label={t('analytics.cohorts.heading')}>
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">
              {t('analytics.cohorts.heading')}
            </h2>
            {data.cohorts.length === 0 ? (
              <p className="mt-2 text-sm text-gray-500">{t('analytics.cohorts.noSignups')}</p>
            ) : (
              <table className="mt-2 w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                    <th scope="col" className="py-2 pr-4">{t('analytics.cohorts.week')}</th>
                    <th scope="col" className="py-2 pr-4">{t('analytics.cohorts.signups')}</th>
                    <th scope="col" className="py-2 pr-4">{t('analytics.cohorts.d7')}</th>
                    <th scope="col" className="py-2">{t('analytics.cohorts.d30')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cohorts.map((c) => (
                    <tr key={c.week_start} className="border-b border-gray-100">
                      <td className="py-2 pr-4 font-medium text-gray-900">{c.week_start}</td>
                      <td className="py-2 pr-4">{c.signups}</td>
                      <td className="py-2 pr-4">{fmtPct(c.d7_pct)}</td>
                      <td className="py-2">{fmtPct(c.d30_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section aria-label={t('analytics.shortcuts.heading')}>
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">{t('analytics.shortcuts.heading')}</h2>
            <div className="mt-2 flex flex-wrap gap-3">
              {Object.entries(data.engagement.quicklink_taps).length === 0 ? (
                <p className="text-sm text-gray-500">{t('analytics.shortcuts.none')}</p>
              ) : (
                Object.entries(data.engagement.quicklink_taps).map(([surface, count]) => (
                  <span key={surface} className="rounded-full border border-gray-200 bg-white px-3 py-1.5 text-sm">
                    <span className="font-semibold text-gray-900">{surface}</span>{' '}
                    <span className="text-gray-600">{count}</span>
                  </span>
                ))
              )}
            </div>
          </section>

          <p className="text-xs text-gray-400">
            {t('analytics.footer')}
          </p>
        </div>
      )}
    </div>
  );
}
