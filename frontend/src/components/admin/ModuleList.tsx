import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useModules, useReorderModules, useDeleteModule, useRestoreModule } from '@/api/admin';
import OrderArrows from './OrderArrows';
import ConfirmDialog from './ConfirmDialog';
import type { AdminModule } from '@/api/admin';

const ARCHIVE_RETENTION_DAYS = 30;

function daysUntilPurge(archivedAt: string): number {
  const elapsed = Math.floor((Date.now() - Date.parse(archivedAt)) / 86_400_000);
  return Math.max(0, ARCHIVE_RETENTION_DAYS - elapsed);
}

export default function ModuleList() {
  const { t } = useTranslation('admin');
  const { data: modules = [], isLoading } = useModules();
  const reorder = useReorderModules();
  const deleteMod = useDeleteModule();
  const restoreMod = useRestoreModule();
  const [deleteTarget, setDeleteTarget] = useState<AdminModule | null>(null);

  // Reordering operates over the ACTIVE list only (archived modules aren't shown
  // there), so swap against the active ordering.
  function handleMove(active: AdminModule[], index: number, direction: 'up' | 'down') {
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= active.length) return;
    const updated = active.map((m, i) => {
      if (i === index) return { id: m.id, order_index: active[swapIdx].order_index };
      if (i === swapIdx) return { id: m.id, order_index: active[index].order_index };
      return { id: m.id, order_index: m.order_index };
    });
    reorder.mutate(updated);
  }

  if (isLoading) return <p className="text-muted-foreground">{t('moduleList.loading')}</p>;

  const sorted = [...modules]
    .filter((m) => !m.archived_at)
    .sort((a, b) => a.order_index - b.order_index);
  const archived = modules
    .filter((m) => !!m.archived_at)
    .sort((a, b) => Date.parse(b.archived_at!) - Date.parse(a.archived_at!));

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-ink">{t('moduleList.heading')}</h2>
        <Link
          to="/admin/modules/new"
          className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700"
        >
          {t('moduleList.newButton')}
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {sorted.map((m, i) => (
          <div
            key={m.id}
            className={`flex items-center gap-3 rounded-lg border bg-card p-3 ${
              m.is_premium ? 'border-accent-500/30' : 'border-line'
            }`}
          >
            <span className="text-xl">{m.icon}</span>
            <div className="flex-1">
              <div className="font-medium text-ink">{m.title}</div>
              <div className="text-xs text-muted-foreground">
                {m.topic} · {t('moduleList.lessonCount', { count: m.lesson_count })}
                {m.country_codes.length > 0 && ` · ${m.country_codes.join(', ')}`}
                {m.is_premium && <span className="ml-1 text-accent-500">{t('moduleList.premium')}</span>}
              </div>
            </div>
            <OrderArrows
              onMoveUp={() => handleMove(sorted, i, 'up')}
              onMoveDown={() => handleMove(sorted, i, 'down')}
              isFirst={i === 0}
              isLast={i === sorted.length - 1}
            />
            <Link to={`/admin/modules/${m.id}/levels`} className="text-xs text-brand-600 hover:text-brand-700">
              {t('moduleList.levelsLink')}
            </Link>
            <Link to={`/admin/modules/${m.id}`} className="text-xs text-brand-600 hover:text-brand-700">
              {t('moduleList.editLink')}
            </Link>
            <button
              type="button"
              onClick={() => setDeleteTarget(m)}
              className="text-xs text-danger-500 hover:text-danger-400"
            >
              {t('moduleList.delete')}
            </button>
          </div>
        ))}
      </div>

      {archived.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('moduleList.archivedHeading')}
          </h3>
          <div className="flex flex-col gap-2">
            {archived.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-3 rounded-lg border border-line bg-muted/40 p-3 opacity-80"
              >
                <span className="text-xl grayscale">{m.icon}</span>
                <div className="flex-1">
                  <div className="font-medium text-ink">{m.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {m.topic} · {t('moduleList.lessonCount', { count: m.lesson_count })}
                    {' · '}
                    {t('moduleList.archivedHint', { days: daysUntilPurge(m.archived_at!) })}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => restoreMod.mutate(m.id)}
                  disabled={restoreMod.isPending}
                  className="text-xs text-brand-600 hover:text-brand-700 disabled:opacity-50"
                >
                  {t('moduleList.restore')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={t('moduleList.deleteTitle', { title: deleteTarget?.title ?? '' })}
        message={t('moduleList.deleteMessage')}
        onConfirm={() => { if (deleteTarget) deleteMod.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
