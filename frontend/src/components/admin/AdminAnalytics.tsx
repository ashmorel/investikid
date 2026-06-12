import { useState } from 'react';
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
  const [days, setDays] = useState<number>(30);
  const { data, isLoading, isError } = useAnalyticsSummary(days);

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Analytics</h1>
        <div role="group" aria-label="Date range" className="flex gap-1">
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
              {r}d
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="mt-6 text-sm text-gray-500">Loading analytics…</p>}
      {isError && (
        <p role="alert" className="mt-6 text-sm font-semibold text-red-700">
          Could not load analytics. Try again shortly.
        </p>
      )}

      {data && (
        <div className="mt-4 space-y-6">
          <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard
              label="Activation"
              value={fmtPct(data.activation.rate_pct)}
              sub={`${data.activation.activated} of ${data.activation.signups} signups did a lesson <24h`}
            />
            <KpiCard
              label="Hero tap-through"
              value={fmtPct(data.engagement.cta_through_pct)}
              sub={`${data.engagement.home_cta_tap} taps / ${data.engagement.home_view} home views`}
            />
            <KpiCard
              label="Lessons completed"
              value={String(data.engagement.lesson_completed)}
              sub={`last ${data.window_days} days`}
            />
            <KpiCard
              label="Digests sent"
              value={String(data.engagement.digest_sent)}
              sub={`last ${data.window_days} days`}
            />
          </section>

          <section aria-label="Trial funnel">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">Trial funnel</h2>
            <div className="mt-2 grid grid-cols-3 gap-3">
              <KpiCard label="Paywall views" value={String(data.funnel.paywall_view)} />
              <KpiCard label="Trials started" value={String(data.funnel.trial_started)} sub="Stripe only (v1)" />
              <KpiCard label="Subscriptions" value={String(data.funnel.subscription_activated)} />
            </div>
          </section>

          <section aria-label="Signup cohorts">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">
              Weekly signup cohorts (last 8 weeks)
            </h2>
            {data.cohorts.length === 0 ? (
              <p className="mt-2 text-sm text-gray-500">No signups in the cohort window yet.</p>
            ) : (
              <table className="mt-2 w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
                    <th scope="col" className="py-2 pr-4">Week</th>
                    <th scope="col" className="py-2 pr-4">Signups</th>
                    <th scope="col" className="py-2 pr-4">D7 retained</th>
                    <th scope="col" className="py-2">D30 retained</th>
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

          <section aria-label="Shortcut taps">
            <h2 className="text-sm font-bold uppercase tracking-wide text-gray-600">Home shortcut taps</h2>
            <div className="mt-2 flex flex-wrap gap-3">
              {Object.entries(data.engagement.quicklink_taps).length === 0 ? (
                <p className="text-sm text-gray-500">None yet.</p>
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
            First-party counts only — no third-party trackers. Raw events auto-delete after 13 months.
            /try demo and Apple/Google trials are not tracked in v1.
          </p>
        </div>
      )}
    </div>
  );
}
