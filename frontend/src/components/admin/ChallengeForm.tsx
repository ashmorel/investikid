import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChallenges, useCreateChallenge, useUpdateChallenge, useBadges } from '@/api/admin';

const CHALLENGE_TYPES = ['lessons_completed', 'xp_earned', 'streak'] as const;

export default function ChallengeForm() {
  const { challengeId } = useParams<{ challengeId: string }>();
  const navigate = useNavigate();
  const isEdit = !!challengeId && challengeId !== 'new';

  const { data: challenges = [] } = useChallenges();
  const { data: badges = [] } = useBadges();
  const existing = isEdit ? challenges.find((c) => c.id === challengeId) : undefined;
  const createChallenge = useCreateChallenge();
  const updateChallenge = useUpdateChallenge();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<string>('lessons_completed');
  const [targetValue, setTargetValue] = useState(1);
  const [xpReward, setXpReward] = useState(50);
  const [badgeId, setBadgeId] = useState<string | null>(null);
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [isPremium, setIsPremium] = useState(false);

  useEffect(() => {
    if (existing) {
      setTitle(existing.title);
      setDescription(existing.description);
      setType(existing.type);
      setTargetValue(existing.target_value);
      setXpReward(existing.xp_reward);
      setBadgeId(existing.badge_id);
      setStartsAt(existing.starts_at.slice(0, 16));
      setEndsAt(existing.ends_at.slice(0, 16));
      setIsPremium(existing.is_premium);
    }
  }, [existing]);

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
      <h2 className="mb-4 text-xl font-semibold text-slate-50">{isEdit ? 'Edit Challenge' : 'New Challenge'}</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="ch-title" className="mb-1 block text-sm text-slate-400">Title</label>
          <input id="ch-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="ch-desc" className="mb-1 block text-sm text-slate-400">Description</label>
          <textarea id="ch-desc" value={description} onChange={(e) => setDescription(e.target.value)} required rows={2}
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-type" className="mb-1 block text-sm text-slate-400">Type</label>
            <select id="ch-type" value={type} onChange={(e) => setType(e.target.value)}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50">
              {CHALLENGE_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="w-28">
            <label htmlFor="ch-target" className="mb-1 block text-sm text-slate-400">Target</label>
            <input id="ch-target" type="number" value={targetValue} onChange={(e) => setTargetValue(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="w-28">
            <label htmlFor="ch-xp" className="mb-1 block text-sm text-slate-400">XP</label>
            <input id="ch-xp" type="number" value={xpReward} onChange={(e) => setXpReward(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
        </div>
        <div>
          <label htmlFor="ch-badge" className="mb-1 block text-sm text-slate-400">Linked Badge (optional)</label>
          <select id="ch-badge" value={badgeId ?? ''} onChange={(e) => setBadgeId(e.target.value || null)}
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50">
            <option value="">None</option>
            {badges.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="ch-starts" className="mb-1 block text-sm text-slate-400">Starts At</label>
            <input id="ch-starts" type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="flex-1">
            <label htmlFor="ch-ends" className="mb-1 block text-sm text-slate-400">Ends At</label>
            <input id="ch-ends" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input id="ch-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800" />
          <label htmlFor="ch-premium" className="text-sm text-slate-400">Premium only</label>
        </div>
        <div className="mt-2 flex gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">Save</button>
          <button type="button" onClick={() => navigate('/admin/challenges')}
            className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">Cancel</button>
        </div>
      </form>
    </div>
  );
}
