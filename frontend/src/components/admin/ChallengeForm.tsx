import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useChallenges, useCreateChallenge, useUpdateChallenge, useBadges } from '@/api/admin';
import type { AdminChallenge, AdminBadge } from '@/api/admin';
import { FormSection } from './FormSection';

const CHALLENGE_TYPES = ['lessons_completed', 'xp_earned', 'streak'] as const;

export default function ChallengeForm() {
  const { challengeId } = useParams<{ challengeId: string }>();
  const { t } = useTranslation('admin');
  const isEdit = !!challengeId && challengeId !== 'new';

  const { data: challenges = [] } = useChallenges();
  const { data: badges = [] } = useBadges();
  const existing = isEdit ? challenges.find((c) => c.id === challengeId) : undefined;

  if (isEdit && !existing) {
    return <div className="text-muted-foreground">{t('challenge.loading')}</div>;
  }

  return <ChallengeFormInner key={existing?.id ?? 'new'} existing={existing} badges={badges} isEdit={isEdit} challengeId={challengeId} />;
}

function ChallengeFormInner({ existing, badges, isEdit, challengeId }: {
  existing?: AdminChallenge;
  badges: AdminBadge[];
  isEdit: boolean;
  challengeId?: string;
}) {
  const { t } = useTranslation('admin');
  const navigate = useNavigate();
  const createChallenge = useCreateChallenge();
  const updateChallenge = useUpdateChallenge();

  const [title, setTitle] = useState(existing?.title ?? '');
  const [description, setDescription] = useState(existing?.description ?? '');
  const [type, setType] = useState<string>(existing?.type ?? 'lessons_completed');
  const [targetValue, setTargetValue] = useState(existing?.target_value ?? 1);
  const [xpReward, setXpReward] = useState(existing?.xp_reward ?? 50);
  const [badgeId, setBadgeId] = useState<string | null>(existing?.badge_id ?? null);
  const [startsAt, setStartsAt] = useState(existing?.starts_at.slice(0, 16) ?? '');
  const [endsAt, setEndsAt] = useState(existing?.ends_at.slice(0, 16) ?? '');
  const [isPremium, setIsPremium] = useState(existing?.is_premium ?? false);
  const [scope, setScope] = useState<'personal' | 'group'>(existing?.scope ?? 'personal');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = {
      title, description,
      type: type as typeof CHALLENGE_TYPES[number],
      target_value: targetValue, xp_reward: xpReward,
      badge_id: badgeId || null,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      is_premium: isPremium,
      scope,
    };
    if (isEdit && challengeId) {
      await updateChallenge.mutateAsync({ id: challengeId, ...data });
    } else {
      await createChallenge.mutateAsync(data);
    }
    navigate('/admin/challenges');
  }

  return (
    <div className="max-w-lg">
      <h2 className="mb-4 text-xl font-semibold text-ink">{isEdit ? t('challenge.editTitle') : t('challenge.newTitle')}</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <FormSection title={t('challenge.form.sectionDetails')}>
        <div>
          <label htmlFor="ch-title" className="mb-1 block text-sm text-ink">{t('challenge.form.title')}</label>
          <input id="ch-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div>
          <label htmlFor="ch-desc" className="mb-1 block text-sm text-ink">{t('challenge.form.description')}</label>
          <textarea id="ch-desc" value={description} onChange={(e) => setDescription(e.target.value)} required rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        </FormSection>

        <FormSection title={t('challenge.form.sectionGoal')}>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-type" className="mb-1 block text-sm text-ink">{t('challenge.form.type')}</label>
            <select id="ch-type" value={type} onChange={(e) => setType(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300">
              {CHALLENGE_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="w-36">
            <label htmlFor="ch-scope" className="mb-1 block text-sm text-ink">{t('challenge.form.scope')}</label>
            <select id="ch-scope" value={scope} onChange={(e) => setScope(e.target.value as 'personal' | 'group')}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300">
              <option value="personal">{t('challenge.form.personal')}</option>
              <option value="group">{t('challenge.form.groupCoop')}</option>
            </select>
          </div>
          <div className="w-28">
            <label htmlFor="ch-target" className="mb-1 block text-sm text-ink">{t('challenge.form.target')}</label>
            <input id="ch-target" type="number" value={targetValue} onChange={(e) => setTargetValue(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
          <div className="w-28">
            <label htmlFor="ch-xp" className="mb-1 block text-sm text-ink">{t('challenge.form.xp')}</label>
            <input id="ch-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
        </div>
        <div>
          <label htmlFor="ch-badge" className="mb-1 block text-sm text-ink">{t('challenge.form.linkedBadge')}</label>
          <select id="ch-badge" value={badgeId ?? ''} onChange={(e) => setBadgeId(e.target.value || null)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300">
            <option value="">{t('challenge.form.noBadge')}</option>
            {badges.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        </FormSection>

        <FormSection title={t('challenge.form.sectionSchedule')}>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-starts" className="mb-1 block text-sm text-ink">{t('challenge.form.startsAt')}</label>
            <input id="ch-starts" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
          <div className="flex-1">
            <label htmlFor="ch-ends" className="mb-1 block text-sm text-ink">{t('challenge.form.endsAt')}</label>
            <input id="ch-ends" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input id="ch-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
            className="h-4 w-4 rounded border-input bg-background" />
          <label htmlFor="ch-premium" className="text-sm text-ink">{t('challenge.form.premiumOnly')}</label>
        </div>
        </FormSection>

        <div className="mt-1 flex gap-3">
          <button type="submit" className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700">{t('challenge.form.save')}</button>
          <button type="button" onClick={() => navigate('/admin/challenges')}
            className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50">{t('challenge.form.cancel')}</button>
        </div>
      </form>
    </div>
  );
}
