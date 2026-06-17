import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useCreateLevel, useUpdateLevel } from '@/api/admin';
import type { AdminLevel } from '@/api/admin';

interface LevelFormProps {
  moduleId: string;
  existing?: AdminLevel;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LevelForm({ moduleId, existing, nextOrderIndex, onClose }: LevelFormProps) {
  const { t } = useTranslation('admin');
  const isEdit = !!existing;
  const createLevel = useCreateLevel(moduleId);
  const updateLevel = useUpdateLevel(moduleId);

  const [title, setTitle] = useState(existing?.title ?? '');
  const [orderIndex, setOrderIndex] = useState(existing?.order_index ?? nextOrderIndex);
  const [isPremium, setIsPremium] = useState(existing?.is_premium ?? false);
  const [passThreshold, setPassThreshold] = useState(existing?.pass_threshold ?? 0.7);
  const [icon, setIcon] = useState(existing?.icon ?? '📊');
  const [objectives, setObjectives] = useState<string[]>(existing?.learning_objectives ?? []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = { title, order_index: orderIndex, is_premium: isPremium, pass_threshold: passThreshold, icon };
    if (isEdit && existing) {
      // learning_objectives is only accepted on update (AdminLevelUpdate), not create.
      const filledObjectives = objectives.map((o) => o.trim()).filter((o) => o.length > 0);
      await updateLevel.mutateAsync({
        id: existing.id,
        ...payload,
        learning_objectives: filledObjectives.length > 0 ? filledObjectives : null,
      });
    } else {
      await createLevel.mutateAsync(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" role="dialog" aria-label={isEdit ? t('levelForm.editAriaLabel') : t('levelForm.addAriaLabel')}>
      <div className="w-full max-w-md rounded-lg border border-line bg-card p-6">
        <h3 className="mb-4 text-lg font-semibold text-ink">{isEdit ? t('levelForm.editTitle') : t('levelForm.addTitle')}</h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          <div>
            <label htmlFor="level-title" className="mb-1 block text-sm text-ink">{t('levelForm.titleLabel')}</label>
            <input
              id="level-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label htmlFor="level-order-index" className="mb-1 block text-sm text-ink">{t('levelForm.orderLabel')}</label>
            <input
              id="level-order-index"
              type="number"
              value={orderIndex}
              onChange={(e) => setOrderIndex(Number(e.target.value))}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label htmlFor="level-pass-threshold" className="mb-1 block text-sm text-ink">{t('levelForm.thresholdLabel')}</label>
            <input
              id="level-pass-threshold"
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={passThreshold}
              onChange={(e) => setPassThreshold(Number(e.target.value))}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label htmlFor="level-icon" className="mb-1 block text-sm text-ink">{t('levelForm.iconLabel')}</label>
            <input
              id="level-icon"
              type="text"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="level-is-premium"
              type="checkbox"
              checked={isPremium}
              onChange={(e) => setIsPremium(e.target.checked)}
              className="h-4 w-4 accent-brand-600"
            />
            <label htmlFor="level-is-premium" className="text-sm text-ink">{t('levelForm.premiumLabel')}</label>
          </div>

          {isEdit && (
          <div>
            <span className="mb-1 block text-sm text-ink">{t('levelForm.objectivesLabel')}</span>
            <div className="flex flex-col gap-2">
              {objectives.map((obj, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    aria-label={t('levelForm.objectiveAriaLabel', { number: i + 1 })}
                    type="text"
                    value={obj}
                    placeholder={t('levelForm.objectivePlaceholder')}
                    onChange={(e) => setObjectives((prev) => prev.map((o, idx) => (idx === i ? e.target.value : o)))}
                    className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
                  />
                  <button
                    type="button"
                    aria-label={t('levelForm.removeObjectiveAriaLabel', { number: i + 1 })}
                    onClick={() => setObjectives((prev) => prev.filter((_, idx) => idx !== i))}
                    className="text-xs text-danger-500"
                  >
                    {t('levelForm.removeObjective')}
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setObjectives((prev) => [...prev, ''])}
              className="mt-2 text-sm text-brand-600 hover:text-brand-700"
            >
              {t('levelForm.addObjective')}
            </button>
          </div>
          )}

          <div>
            <p className="text-xs text-muted-foreground">{t('levelForm.contentSource')} <span className="text-muted-foreground">{t('levelForm.contentSourceValue')}</span></p>
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700"
            >
              {t('levelForm.save')}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50"
            >
              {t('levelForm.cancel')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
