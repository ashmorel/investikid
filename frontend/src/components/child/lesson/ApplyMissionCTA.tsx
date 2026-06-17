import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { type ActiveMission } from '@/api/missions';

export function ApplyMissionCTA({ mission }: { mission: ActiveMission }) {
  const { t } = useTranslation('lessons');
  return (
    <section
      aria-label={t('mission.sectionLabel')}
      className="mt-4 rounded-2xl border-2 border-brand-200 bg-brand-50 p-5 text-center"
    >
      <p className="text-sm font-bold uppercase tracking-wider text-brand-700">{t('mission.label')}</p>
      <p className="mt-1 text-lg font-extrabold text-ink">{mission.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{mission.prompt}</p>
      <Link
        to={`/simulator?mission=${mission.id}`}
        className="mt-3 inline-block rounded-full bg-brand-gradient px-5 py-2.5 text-sm font-bold text-white shadow"
      >
        {t('mission.cta')}
      </Link>
    </section>
  );
}
