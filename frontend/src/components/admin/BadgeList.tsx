import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useBadges, useDeleteBadge, badgeIcon } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminBadge } from '@/api/admin';

export default function BadgeList() {
  const { data: badges = [], isLoading } = useBadges();
  const deleteBadge = useDeleteBadge();
  const [deleteTarget, setDeleteTarget] = useState<AdminBadge | null>(null);

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Badges</h2>
        <Link to="/admin/badges/new" className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500">
          + New Badge
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {badges.map((b) => (
          <div key={b.id} className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3">
            <span className="text-xl" aria-hidden="true">{badgeIcon(b)}</span>
            <div className="flex-1">
              <div className="font-medium text-slate-50">{b.name}</div>
              <div className="text-xs text-slate-500">{b.condition_type} ≥ {b.condition_value}</div>
            </div>
            <Link to={`/admin/badges/${b.id}`} className="text-xs text-blue-400 hover:text-blue-300">Edit</Link>
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
