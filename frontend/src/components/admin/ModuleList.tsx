import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useModules, useReorderModules, useDeleteModule } from '@/api/admin';
import OrderArrows from './OrderArrows';
import ConfirmDialog from './ConfirmDialog';
import type { AdminModule } from '@/api/admin';

export default function ModuleList() {
  const { data: modules = [], isLoading } = useModules();
  const reorder = useReorderModules();
  const deleteMod = useDeleteModule();
  const [deleteTarget, setDeleteTarget] = useState<AdminModule | null>(null);

  function handleMove(index: number, direction: 'up' | 'down') {
    const sorted = [...modules].sort((a, b) => a.order_index - b.order_index);
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;
    const updated = sorted.map((m, i) => {
      if (i === index) return { id: m.id, order_index: sorted[swapIdx].order_index };
      if (i === swapIdx) return { id: m.id, order_index: sorted[index].order_index };
      return { id: m.id, order_index: m.order_index };
    });
    reorder.mutate(updated);
  }

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  const sorted = [...modules].sort((a, b) => a.order_index - b.order_index);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Modules</h2>
        <Link
          to="/admin/modules/new"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
        >
          + New Module
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {sorted.map((m, i) => (
          <div
            key={m.id}
            className={`flex items-center gap-3 rounded-lg border bg-slate-900 p-3 ${
              m.is_premium ? 'border-accent-500/30' : 'border-slate-700'
            }`}
          >
            <span className="text-xl">{m.icon}</span>
            <div className="flex-1">
              <div className="font-medium text-slate-50">{m.title}</div>
              <div className="text-xs text-slate-500">
                {m.topic} · {m.lesson_count} lessons
                {m.country_codes.length > 0 && ` · ${m.country_codes.join(', ')}`}
                {m.is_premium && <span className="ml-1 text-accent-500">⭐ Premium</span>}
              </div>
            </div>
            <OrderArrows
              onMoveUp={() => handleMove(i, 'up')}
              onMoveDown={() => handleMove(i, 'down')}
              isFirst={i === 0}
              isLast={i === sorted.length - 1}
            />
            <Link to={`/admin/modules/${m.id}/levels`} className="text-xs text-blue-400 hover:text-blue-300">
              Levels
            </Link>
            <Link to={`/admin/modules/${m.id}`} className="text-xs text-blue-400 hover:text-blue-300">
              Edit
            </Link>
            <button
              type="button"
              onClick={() => setDeleteTarget(m)}
              className="text-xs text-danger-500 hover:text-danger-400"
            >
              Delete
            </button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.title}"?`}
        message="This will permanently delete the module and all its lessons."
        onConfirm={() => { if (deleteTarget) deleteMod.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
