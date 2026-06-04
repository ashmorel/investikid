import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useBadges, useDeleteBadge, badgeIcon } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminBadge } from '@/api/admin';

export default function BadgeList() {
  const { data: badges = [], isLoading } = useBadges();
  const deleteBadge = useDeleteBadge();
  const [deleteTarget, setDeleteTarget] = useState<AdminBadge | null>(null);

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-ink">Badges</h2>
        <Link to="/admin/badges/new" className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700">
          + New Badge
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {badges.map((b) => (
          <div key={b.id} className="flex items-center gap-3 rounded-lg border border-line bg-card p-3">
            <span className="text-xl" aria-hidden="true">{badgeIcon(b)}</span>
            <div className="flex-1">
              <div className="font-medium text-ink">{b.name}</div>
              <div className="text-xs text-muted-foreground">{b.condition_type} ≥ {b.condition_value}</div>
            </div>
            <Link to={`/admin/badges/${b.id}`} className="text-xs text-brand-600 hover:text-brand-700">Edit</Link>
            <button type="button" onClick={() => setDeleteTarget(b)} className="text-xs text-danger-500 hover:text-danger-400">Delete</button>
          </div>
        ))}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.name}"?`}
        message="This badge will be permanently deleted. Deletion will fail if users have earned it."
        onConfirm={() => { if (deleteTarget) deleteBadge.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
