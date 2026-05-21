import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useChallenges, useDeleteChallenge } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';
import type { AdminChallenge } from '@/api/admin';

export default function ChallengeList() {
  const { data: challenges = [], isLoading } = useChallenges();
  const deleteChallenge = useDeleteChallenge();
  const [deleteTarget, setDeleteTarget] = useState<AdminChallenge | null>(null);

  if (isLoading) return <p className="text-slate-400">Loading...</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-50">Challenges</h2>
        <Link to="/admin/challenges/new" className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-500">
          + New Challenge
        </Link>
      </div>
      <div className="flex flex-col gap-2">
        {challenges.map((c) => {
          const now = new Date();
          const isActive = new Date(c.starts_at) <= now && now <= new Date(c.ends_at);
          return (
            <div key={c.id} className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3">
              <div className="flex-1">
                <div className="font-medium text-slate-50">{c.title}</div>
                <div className="text-xs text-slate-500">
                  {c.type} · target: {c.target_value} · {c.xp_reward} XP
                  {c.is_premium && <span className="ml-1 text-yellow-500">⭐</span>}
                </div>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs ${isActive ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'}`}>
                {isActive ? 'Active' : 'Expired'}
              </span>
              <Link to={`/admin/challenges/${c.id}`} className="text-xs text-blue-400 hover:text-blue-300">Edit</Link>
              <button type="button" onClick={() => setDeleteTarget(c)} className="text-xs text-red-400 hover:text-red-300">Delete</button>
            </div>
          );
        })}
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete "${deleteTarget?.title}"?`}
        message="This challenge will be permanently deleted."
        onConfirm={() => { if (deleteTarget) deleteChallenge.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
