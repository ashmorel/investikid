import { useState } from 'react';
import { useCreateLevel, useUpdateLevel } from '@/api/admin';
import type { AdminLevel } from '@/api/admin';

interface LevelFormProps {
  moduleId: string;
  existing?: AdminLevel;
  nextOrderIndex: number;
  onClose: () => void;
}

export default function LevelForm({ moduleId, existing, nextOrderIndex, onClose }: LevelFormProps) {
  const isEdit = !!existing;
  const createLevel = useCreateLevel(moduleId);
  const updateLevel = useUpdateLevel(moduleId);

  const [title, setTitle] = useState(existing?.title ?? '');
  const [orderIndex, setOrderIndex] = useState(existing?.order_index ?? nextOrderIndex);
  const [isPremium, setIsPremium] = useState(existing?.is_premium ?? false);
  const [passThreshold, setPassThreshold] = useState(existing?.pass_threshold ?? 0.7);
  const [icon, setIcon] = useState(existing?.icon ?? '📊');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = { title, order_index: orderIndex, is_premium: isPremium, pass_threshold: passThreshold, icon };
    if (isEdit && existing) {
      await updateLevel.mutateAsync({ id: existing.id, ...payload });
    } else {
      await createLevel.mutateAsync(payload);
    }
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" role="dialog" aria-label={isEdit ? 'Edit level' : 'Add level'}>
      <div className="w-full max-w-md rounded-lg border border-line bg-card p-6">
        <h3 className="mb-4 text-lg font-semibold text-ink">{isEdit ? 'Edit Level' : 'Add Level'}</h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          <div>
            <label htmlFor="level-title" className="mb-1 block text-sm text-ink">Title</label>
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
            <label htmlFor="level-order-index" className="mb-1 block text-sm text-ink">Order index</label>
            <input
              id="level-order-index"
              type="number"
              value={orderIndex}
              onChange={(e) => setOrderIndex(Number(e.target.value))}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
            />
          </div>

          <div>
            <label htmlFor="level-pass-threshold" className="mb-1 block text-sm text-ink">Pass threshold (0–1)</label>
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
            <label htmlFor="level-icon" className="mb-1 block text-sm text-ink">Icon</label>
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
            <label htmlFor="level-is-premium" className="text-sm text-ink">Premium</label>
          </div>

          <div>
            <p className="text-xs text-muted-foreground">Content source: <span className="text-muted-foreground">authored</span></p>
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700"
            >
              Save
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
