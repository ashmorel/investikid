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
      <div className="w-full max-w-md rounded-lg border border-slate-700 bg-slate-900 p-6">
        <h3 className="mb-4 text-lg font-semibold text-slate-50">{isEdit ? 'Edit Level' : 'Add Level'}</h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          <div>
            <label htmlFor="level-title" className="mb-1 block text-sm text-slate-400">Title</label>
            <input
              id="level-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="level-order-index" className="mb-1 block text-sm text-slate-400">Order index</label>
            <input
              id="level-order-index"
              type="number"
              value={orderIndex}
              onChange={(e) => setOrderIndex(Number(e.target.value))}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="level-pass-threshold" className="mb-1 block text-sm text-slate-400">Pass threshold (0–1)</label>
            <input
              id="level-pass-threshold"
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={passThreshold}
              onChange={(e) => setPassThreshold(Number(e.target.value))}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="level-icon" className="mb-1 block text-sm text-slate-400">Icon</label>
            <input
              id="level-icon"
              type="text"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-50 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              id="level-is-premium"
              type="checkbox"
              checked={isPremium}
              onChange={(e) => setIsPremium(e.target.checked)}
              className="h-4 w-4 accent-blue-500"
            />
            <label htmlFor="level-is-premium" className="text-sm text-slate-400">Premium</label>
          </div>

          <div>
            <p className="text-xs text-slate-500">Content source: <span className="text-slate-400">authored</span></p>
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500"
            >
              Save
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
