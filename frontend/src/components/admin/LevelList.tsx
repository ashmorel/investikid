import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useLevels, useDeleteLevel, useUpdateLevel } from '@/api/admin';
import type { AdminLevel } from '@/api/admin';
import OrderArrows from './OrderArrows';
import ConfirmDialog from './ConfirmDialog';
import LevelForm from './LevelForm';

export default function LevelList() {
  const { moduleId = '' } = useParams<{ moduleId: string }>();
  const { data: levels = [], isLoading } = useLevels(moduleId);
  const deleteLevel = useDeleteLevel(moduleId);
  const updateLevel = useUpdateLevel(moduleId);

  const [editingLevel, setEditingLevel] = useState<AdminLevel | null>(null);
  const [showNewLevel, setShowNewLevel] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminLevel | null>(null);

  const sorted = [...levels].sort((a, b) => a.order_index - b.order_index);

  function handleMove(index: number, direction: 'up' | 'down') {
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;
    const current = sorted[index];
    const neighbour = sorted[swapIdx];
    updateLevel.mutate({ id: current.id, order_index: neighbour.order_index });
    updateLevel.mutate({ id: neighbour.id, order_index: current.order_index });
  }

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <div className="mb-2">
        <Link to="/admin/modules" className="text-xs text-slate-400 hover:text-slate-200">
          ← Back to modules
        </Link>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Levels</h2>
        <button
          type="button"
          onClick={() => { setEditingLevel(null); setShowNewLevel(true); }}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500"
        >
          + Add Level
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {sorted.map((level, i) => (
          <div
            key={level.id}
            className={`flex items-center gap-3 rounded-lg border bg-slate-900 p-3 ${
              level.is_premium ? 'border-yellow-500/30' : 'border-slate-700'
            }`}
          >
            <OrderArrows
              onMoveUp={() => handleMove(i, 'up')}
              onMoveDown={() => handleMove(i, 'down')}
              isFirst={i === 0}
              isLast={i === sorted.length - 1}
            />
            <span className="text-xl">{level.icon}</span>
            <div className="flex-1">
              <div className="font-medium text-slate-50">{level.title}</div>
              <div className="text-xs text-slate-500">
                {level.lesson_count} lessons
                {level.is_premium && <span className="ml-1 text-yellow-500">⭐ Premium</span>}
              </div>
            </div>
            <Link
              to={`/admin/modules/${moduleId}/levels/${level.id}/lessons`}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              Lessons
            </Link>
            <button
              type="button"
              onClick={() => { setEditingLevel(level); setShowNewLevel(false); }}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setDeleteTarget(level)}
              className="text-xs text-red-400 hover:text-red-300"
            >
              Delete
            </button>
          </div>
        ))}
      </div>

      {(editingLevel || showNewLevel) && (
        <LevelForm
          moduleId={moduleId}
          existing={editingLevel ?? undefined}
          nextOrderIndex={sorted.length}
          onClose={() => { setEditingLevel(null); setShowNewLevel(false); }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.title}"?`}
        message="This will permanently delete this level and all its lessons."
        onConfirm={() => { if (deleteTarget) deleteLevel.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
