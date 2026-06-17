import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLevels, useDeleteLevel, useUpdateLevel } from '@/api/admin';
import type { AdminLevel } from '@/api/admin';
import OrderArrows from './OrderArrows';
import ConfirmDialog from './ConfirmDialog';
import LevelForm from './LevelForm';

export default function LevelList() {
  const { t } = useTranslation('admin');
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

  if (isLoading) return <p className="text-muted-foreground">{t('levelList.loading')}</p>;

  return (
    <div>
      <div className="mb-2">
        <Link to="/admin/modules" className="text-xs text-muted-foreground hover:text-ink">
          {t('levelList.backToModules')}
        </Link>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-ink">{t('levelList.heading')}</h2>
        <button
          type="button"
          onClick={() => { setEditingLevel(null); setShowNewLevel(true); }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700"
        >
          {t('levelList.addLevel')}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {sorted.map((level, i) => (
          <div
            key={level.id}
            className={`flex items-center gap-3 rounded-lg border bg-card p-3 ${
              level.is_premium ? 'border-accent-500/30' : 'border-line'
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
              <div className="font-medium text-ink">{level.title}</div>
              <div className="text-xs text-muted-foreground">
                {t('levelList.lessons', { count: level.lesson_count })}
                {level.is_premium && <span className="ml-1 text-accent-500">{t('levelList.premium')}</span>}
              </div>
            </div>
            <Link
              to={`/admin/modules/${moduleId}/levels/${level.id}/lessons`}
              className="text-xs text-brand-600 hover:text-brand-700"
            >
              {t('levelList.levelsLink')}
            </Link>
            <button
              type="button"
              onClick={() => { setEditingLevel(level); setShowNewLevel(false); }}
              className="text-xs text-brand-600 hover:text-brand-700"
            >
              {t('levelList.edit')}
            </button>
            <button
              type="button"
              onClick={() => setDeleteTarget(level)}
              className="text-xs text-danger-500 hover:text-danger-400"
            >
              {t('levelList.delete')}
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
        title={t('levelList.deleteTitle', { title: deleteTarget?.title ?? '' })}
        message={t('levelList.deleteMessage')}
        onConfirm={() => { if (deleteTarget) deleteLevel.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
