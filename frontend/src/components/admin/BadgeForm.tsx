import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBadges, useCreateBadge, useUpdateBadge } from '@/api/admin';
import type { AdminBadge } from '@/api/admin';

const CONDITION_TYPES = ['lesson_count', 'streak_days', 'module_complete', 'xp_total'] as const;

export default function BadgeForm() {
  const { badgeId } = useParams<{ badgeId: string }>();
  const isEdit = !!badgeId && badgeId !== 'new';

  const { data: badges = [] } = useBadges();
  const existing = isEdit ? badges.find((b) => b.id === badgeId) : undefined;

  if (isEdit && !existing) {
    return <div className="text-muted-foreground">Loading…</div>;
  }

  return <BadgeFormInner key={existing?.id ?? 'new'} existing={existing} isEdit={isEdit} badgeId={badgeId} />;
}

function BadgeFormInner({ existing, isEdit, badgeId }: { existing?: AdminBadge; isEdit: boolean; badgeId?: string }) {
  const navigate = useNavigate();
  const createBadge = useCreateBadge();
  const updateBadge = useUpdateBadge();

  const [name, setName] = useState(existing?.name ?? '');
  const [description, setDescription] = useState(existing?.description ?? '');
  const [iconUrl, setIconUrl] = useState(existing?.icon_url ?? '🏅');
  const [conditionType, setConditionType] = useState<string>(existing?.condition_type ?? 'lesson_count');
  const [conditionValue, setConditionValue] = useState(existing?.condition_value ?? 1);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = { name, description, icon_url: iconUrl, condition_type: conditionType as typeof CONDITION_TYPES[number], condition_value: conditionValue };
    if (isEdit && badgeId) {
      await updateBadge.mutateAsync({ id: badgeId, ...data });
    } else {
      await createBadge.mutateAsync(data);
    }
    navigate('/admin/badges');
  }

  return (
    <div className="max-w-lg">
      <h2 className="mb-4 text-xl font-semibold text-ink">{isEdit ? 'Edit Badge' : 'New Badge'}</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="badge-name" className="mb-1 block text-sm text-ink">Name</label>
          <input id="badge-name" value={name} onChange={(e) => setName(e.target.value)} required
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div>
          <label htmlFor="badge-desc" className="mb-1 block text-sm text-ink">Description</label>
          <textarea id="badge-desc" value={description} onChange={(e) => setDescription(e.target.value)} required rows={2}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div>
          <label htmlFor="badge-icon" className="mb-1 block text-sm text-ink">Icon</label>
          <input id="badge-icon" value={iconUrl} onChange={(e) => setIconUrl(e.target.value)} required
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="badge-cond-type" className="mb-1 block text-sm text-ink">Condition Type</label>
            <select id="badge-cond-type" value={conditionType} onChange={(e) => setConditionType(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300">
              {CONDITION_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div className="w-32">
            <label htmlFor="badge-cond-val" className="mb-1 block text-sm text-ink">Value</label>
            <input id="badge-cond-val" type="number" value={conditionValue} onChange={(e) => setConditionValue(Number(e.target.value))} min={1} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
        </div>
        <div className="mt-2 flex gap-3">
          <button type="submit" className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700">Save</button>
          <button type="button" onClick={() => navigate('/admin/badges')}
            className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50">Cancel</button>
        </div>
      </form>
    </div>
  );
}
