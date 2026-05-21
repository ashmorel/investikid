import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useModules, useCreateModule, useUpdateModule,
  useLessons, useDeleteLesson, useReorderLessons,
  useCountries,
} from '@/api/admin';
import type { AdminLesson } from '@/api/admin';
import OrderArrows from './OrderArrows';
import LessonForm from './LessonForm';
import ConfirmDialog from './ConfirmDialog';

export default function ModuleForm() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const isEdit = !!moduleId && moduleId !== 'new';

  const { data: modules = [] } = useModules();
  const existing = isEdit ? modules.find((m) => m.id === moduleId) : undefined;
  const { data: lessons = [] } = useLessons(isEdit ? moduleId : '');
  const { data: countries = [] } = useCountries();

  const createMod = useCreateModule();
  const updateMod = useUpdateModule();
  const deleteLesson = useDeleteLesson();
  const reorderLessons = useReorderLessons();

  const [topic, setTopic] = useState('');
  const [title, setTitle] = useState('');
  const [icon, setIcon] = useState('📚');
  const [isPremium, setIsPremium] = useState(false);
  const [countryCodes, setCountryCodes] = useState<string[]>([]);
  const [editingLesson, setEditingLesson] = useState<AdminLesson | null>(null);
  const [showNewLesson, setShowNewLesson] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminLesson | null>(null);

  useEffect(() => {
    if (existing) {
      setTopic(existing.topic);
      setTitle(existing.title);
      setIcon(existing.icon);
      setIsPremium(existing.is_premium);
      setCountryCodes(existing.country_codes);
    }
  }, [existing]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && moduleId) {
      await updateMod.mutateAsync({ id: moduleId, topic, title, icon, is_premium: isPremium, country_codes: countryCodes });
    } else {
      const maxOrder = modules.reduce((max, m) => Math.max(max, m.order_index), -1);
      await createMod.mutateAsync({ topic, title, icon, is_premium: isPremium, country_codes: countryCodes, order_index: maxOrder + 1 });
    }
    navigate('/admin/modules');
  }

  function toggleCountry(code: string) {
    setCountryCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function handleLessonMove(index: number, direction: 'up' | 'down') {
    const sorted = [...lessons].sort((a, b) => a.order_index - b.order_index);
    const swapIdx = direction === 'up' ? index - 1 : index + 1;
    if (swapIdx < 0 || swapIdx >= sorted.length) return;
    const updated = sorted.map((l, i) => {
      if (i === index) return { id: l.id, order_index: sorted[swapIdx].order_index };
      if (i === swapIdx) return { id: l.id, order_index: sorted[index].order_index };
      return { id: l.id, order_index: l.order_index };
    });
    if (moduleId) reorderLessons.mutate({ moduleId, order: updated });
  }

  const sortedLessons = [...lessons].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="max-w-2xl">
      <h2 className="mb-4 text-xl font-semibold text-slate-50">
        {isEdit ? 'Edit Module' : 'New Module'}
      </h2>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div>
          <label htmlFor="mod-topic" className="mb-1 block text-sm text-slate-400">Topic</label>
          <input id="mod-topic" value={topic} onChange={(e) => setTopic(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div>
          <label htmlFor="mod-title" className="mb-1 block text-sm text-slate-400">Title</label>
          <input id="mod-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="mod-icon" className="mb-1 block text-sm text-slate-400">Icon</label>
            <input id="mod-icon" value={icon} onChange={(e) => setIcon(e.target.value)} required
              className="w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50" />
          </div>
          <div className="flex items-end gap-2 pb-2">
            <input id="mod-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800" />
            <label htmlFor="mod-premium" className="text-sm text-slate-400">Premium</label>
          </div>
        </div>
        <div>
          <span className="mb-1 block text-sm text-slate-400">Countries (empty = global)</span>
          <div className="flex flex-wrap gap-2">
            {countries.map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => toggleCountry(code)}
                className={`rounded-md px-3 py-1 text-xs ${
                  countryCodes.includes(code)
                    ? 'bg-blue-600 text-white'
                    : 'border border-slate-600 bg-slate-800 text-slate-400'
                }`}
              >
                {code}
              </button>
            ))}
          </div>
        </div>

        {/* Lessons section — only in edit mode */}
        {isEdit && moduleId && (
          <div className="mt-4 border-t border-slate-700 pt-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-medium text-slate-50">Lessons ({sortedLessons.length})</h3>
              <button type="button" onClick={() => { setEditingLesson(null); setShowNewLesson(true); }}
                className="text-sm text-blue-400 hover:text-blue-300">+ Add Lesson</button>
            </div>
            <div className="flex flex-col gap-2">
              {sortedLessons.map((l, i) => (
                <div key={l.id} className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                  <OrderArrows
                    onMoveUp={() => handleLessonMove(i, 'up')}
                    onMoveDown={() => handleLessonMove(i, 'down')}
                    isFirst={i === 0}
                    isLast={i === sortedLessons.length - 1}
                  />
                  <span className={`rounded px-2 py-0.5 text-xs ${
                    l.type === 'card' ? 'bg-blue-500/20 text-blue-400'
                    : l.type === 'quiz' ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                  }`}>{l.type}</span>
                  <span className="flex-1 truncate text-sm text-slate-50">
                    {(l.content_json as Record<string, string>).title
                      || (l.content_json as Record<string, string>).question
                      || (l.content_json as Record<string, string>).prompt
                      || 'Untitled'}
                  </span>
                  <span className="text-xs text-slate-500">{l.xp_reward} XP</span>
                  <button type="button" onClick={() => { setEditingLesson(l); setShowNewLesson(false); }}
                    className="text-xs text-blue-400">Edit</button>
                  <button type="button" onClick={() => setDeleteTarget(l)}
                    className="text-xs text-red-400">Delete</button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 flex gap-3">
          <button type="submit" className="rounded-md bg-blue-600 px-6 py-2 text-sm text-white hover:bg-blue-500">
            Save
          </button>
          <button type="button" onClick={() => navigate('/admin/modules')}
            className="rounded-md border border-slate-600 px-6 py-2 text-sm text-slate-300 hover:bg-slate-800">
            Cancel
          </button>
        </div>
      </form>

      {/* Lesson edit/create modal */}
      {(editingLesson || showNewLesson) && moduleId && (
        <LessonForm
          moduleId={moduleId}
          lesson={editingLesson ?? undefined}
          nextOrderIndex={sortedLessons.length}
          onClose={() => { setEditingLesson(null); setShowNewLesson(false); }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={`Delete lesson?`}
        message="This will permanently delete this lesson."
        onConfirm={() => { if (deleteTarget) deleteLesson.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
