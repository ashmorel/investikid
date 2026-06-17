import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useChallenges, useDeleteChallenge } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminChallenge } from '@/api/admin';

export default function ChallengeList() {
  const { t } = useTranslation('admin');
  const { data: challenges = [], isLoading } = useChallenges();
  const deleteChallenge = useDeleteChallenge();
  const [deleteTarget, setDeleteTarget] = useState<AdminChallenge | null>(null);

  if (isLoading) return <p className="text-muted-foreground">{t('challengeList.loading')}</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-ink">{t('challengeList.heading')}</h2>
        <Link to="/admin/challenges/new" className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700">
          {t('challengeList.newButton')}
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {challenges.map((c) => {
          const now = new Date();
          const isActive = new Date(c.starts_at) <= now && now <= new Date(c.ends_at);
          return (
            <div key={c.id} className="flex items-center gap-3 rounded-lg border border-line bg-card p-3">
              <div className="flex-1">
                <div className="font-medium text-ink">{c.title}</div>
                <div className="text-xs text-muted-foreground">
                  {t('challengeList.typeSummary', { type: c.type, target: c.target_value, xp: c.xp_reward })}
                  {c.is_premium && <span className="ml-1 text-accent-500">⭐</span>}
                  {c.scope === 'group' && (
                    <span className="ml-1 rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-bold text-brand-800">{t('challengeList.groupBadge')}</span>
                  )}
                </div>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs ${isActive ? 'bg-success-500/20 text-success-600' : 'bg-brand-50 text-muted-foreground'}`}>
                {isActive ? t('challengeList.active') : t('challengeList.expired')}
              </span>
              <Link to={`/admin/challenges/${c.id}`} className="text-xs text-brand-600 hover:text-brand-700">{t('challengeList.edit')}</Link>
              <button type="button" onClick={() => setDeleteTarget(c)} className="text-xs text-danger-500 hover:text-danger-400">{t('challengeList.delete')}</button>
            </div>
          );
        })}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={t('challengeList.deleteTitle', { title: deleteTarget?.title ?? '' })}
        message={t('challengeList.deleteMessage')}
        onConfirm={() => { if (deleteTarget) deleteChallenge.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
