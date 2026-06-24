import { useTranslation } from 'react-i18next';
import type { LeaderboardRow } from '@/api/gamification';
import { countryFlag } from '@/lib/country';
import { cn } from '@/lib/utils';

type Props = { rows: LeaderboardRow[]; currentName: string; pointsLabel: string };

export function LeaderboardTable({ rows, pointsLabel }: Props) {
  const { t } = useTranslation('child');
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colRank')}</th>
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colName')}</th>
            <th className="px-4 py-3 text-left font-medium">{t('leaderboard.colCountry')}</th>
            <th className="px-4 py-3 text-right font-medium">{pointsLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.rank}-${r.name}`} className={cn('border-b last:border-b-0', r.is_me && 'bg-brand-50 font-bold')}>
              <td className="px-4 py-3">{r.rank}</td>
              <td className="px-4 py-3">{r.name}</td>
              <td className="px-4 py-3" aria-hidden="true">{r.country_code ? countryFlag(r.country_code) : ''}</td>
              <td className="px-4 py-3 text-right">{r.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
