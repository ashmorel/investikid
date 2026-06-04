import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useModules, useCreateModule, useUpdateModule,
  useLessons, useDeleteLesson, useReorderLessons,
  useCountries, lessonLabel,
} from '@/api/admin';
import type { AdminModule, AdminLesson } from '@/api/admin';
import OrderArrows from './OrderArrows';
import LessonForm from './LessonForm';
import ConfirmDialog from './ConfirmDialog';
import ModuleEngagement from './ModuleEngagement';

export default function ModuleForm() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const isEdit = !!moduleId && moduleId !== 'new';

  const { data: modules = [] } = useModules();
  const existing = isEdit ? modules.find((m) => m.id === moduleId) : undefined;
  const { data: lessons = [] } = useLessons(isEdit ? moduleId : '');
  const { data: countries = [] } = useCountries();

  // Wait for data to load in edit mode before rendering the form
  if (isEdit && !existing) {
    return <div className="text-muted-foreground">Loading…</div>;
  }

  return <ModuleFormInner key={existing?.id ?? 'new'} existing={existing} modules={modules} lessons={lessons} countries={countries} isEdit={isEdit} moduleId={moduleId} />;
}

function ModuleFormInner({ existing, modules, lessons, countries, isEdit, moduleId }: {
  existing?: AdminModule;
  modules: AdminModule[];
  lessons: AdminLesson[];
  countries: string[];
  isEdit: boolean;
  moduleId?: string;
}) {
  const navigate = useNavigate();
  const createMod = useCreateModule();
  const updateMod = useUpdateModule();
  const deleteLesson = useDeleteLesson();
  const reorderLessons = useReorderLessons();

  const [topic, setTopic] = useState(existing?.topic ?? '');
  const [title, setTitle] = useState(existing?.title ?? '');
  const [icon, setIcon] = useState(existing?.icon ?? '📚');
  const [isPremium, setIsPremium] = useState(existing?.is_premium ?? false);
  const [countryCodes, setCountryCodes] = useState<string[]>(existing?.country_codes ?? []);
  const [prerequisiteIds, setPrerequisiteIds] = useState<string[]>(existing?.prerequisite_ids ?? []);
  const [minAge, setMinAge] = useState<string>(existing?.min_age?.toString() ?? '');
  const [maxAge, setMaxAge] = useState<string>(existing?.max_age?.toString() ?? '');
  const [editingLesson, setEditingLesson] = useState<AdminLesson | null>(null);
  const [showNewLesson, setShowNewLesson] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminLesson | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const moduleData = {
      topic, title, icon,
      is_premium: isPremium,
      country_codes: countryCodes,
      prerequisite_ids: prerequisiteIds,
      min_age: minAge ? Number(minAge) : null,
      max_age: maxAge ? Number(maxAge) : null,
    };
    if (isEdit && moduleId) {
      await updateMod.mutateAsync({ id: moduleId, ...moduleData });
    } else {
      const maxOrder = modules.reduce((max, m) => Math.max(max, m.order_index), -1);
      await createMod.mutateAsync({ ...moduleData, order_index: maxOrder + 1 });
    }
    navigate('/admin/modules');
  }

  function toggleCountry(code: string) {
    setCountryCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function togglePrerequisite(id: string) {
    setPrerequisiteIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
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
      <h2 className="mb-4 text-xl font-semibold text-ink">
        {isEdit ? 'Edit Module' : 'New Module'}
      </h2>
      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div>
          <label htmlFor="mod-topic" className="mb-1 block text-sm text-ink">Topic</label>
          <input id="mod-topic" value={topic} onChange={(e) => setTopic(e.target.value)} required
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div>
          <label htmlFor="mod-title" className="mb-1 block text-sm text-ink">Title</label>
          <input id="mod-title" value={title} onChange={(e) => setTitle(e.target.value)} required
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="mod-icon" className="mb-1 block text-sm text-ink">Icon</label>
            <input id="mod-icon" value={icon} onChange={(e) => setIcon(e.target.value)} required
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
          <div className="flex items-end gap-2 pb-2">
            <input id="mod-premium" type="checkbox" checked={isPremium} onChange={(e) => setIsPremium(e.target.checked)}
              className="h-4 w-4 rounded border-input bg-background" />
            <label htmlFor="mod-premium" className="text-sm text-ink">Premium</label>
          </div>
        </div>
        <div>
          <span className="mb-1 block text-sm text-ink">Countries (empty = global)</span>
          <div className="flex flex-wrap gap-2">
            {countries.map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => toggleCountry(code)}
                className={`rounded-md px-3 py-1 text-xs ${
                  countryCodes.includes(code)
                    ? 'bg-brand-600 text-white'
                    : 'border border-input bg-background text-muted-foreground'
                }`}
              >
                {code}
              </button>
            ))}
          </div>
        </div>

        {/* Prerequisites */}
        <div>
          <span className="mb-1 block text-sm text-ink">Prerequisites (optional)</span>
          <div className="flex flex-wrap gap-2">
            {modules
              .filter((m) => m.id !== moduleId)
              .map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => togglePrerequisite(m.id)}
                  className={`rounded-md px-3 py-1 text-xs ${
                    prerequisiteIds.includes(m.id)
                      ? 'bg-purple-600 text-white'
                      : 'border border-input bg-background text-muted-foreground'
                  }`}
                >
                  {m.icon} {m.title}
                </button>
              ))}
          </div>
        </div>

        {/* Age Range */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label htmlFor="mod-min-age" className="mb-1 block text-sm text-ink">Min Age</label>
            <input id="mod-min-age" type="number" value={minAge} onChange={(e) => setMinAge(e.target.value)}
              min={1} max={99} placeholder="Any"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
          <div className="flex-1">
            <label htmlFor="mod-max-age" className="mb-1 block text-sm text-ink">Max Age</label>
            <input id="mod-max-age" type="number" value={maxAge} onChange={(e) => setMaxAge(e.target.value)}
              min={1} max={99} placeholder="Any"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300" />
          </div>
          <p className="self-end pb-2 text-xs text-muted-foreground">Leave empty for all ages</p>
        </div>

        {/* Lessons section — only in edit mode */}
        {isEdit && moduleId && (
          <div className="mt-4 border-t border-line pt-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-medium text-ink">Lessons ({sortedLessons.length})</h3>
              <button type="button" onClick={() => { setEditingLesson(null); setShowNewLesson(true); }}
                className="text-sm text-brand-600 hover:text-brand-700">+ Add Lesson</button>
            </div>
            <div className="flex flex-col gap-2">
              {sortedLessons.map((l, i) => (
                <div key={l.id} className="flex items-center gap-2 rounded-md border border-line bg-card px-3 py-2">
                  <OrderArrows
                    onMoveUp={() => handleLessonMove(i, 'up')}
                    onMoveDown={() => handleLessonMove(i, 'down')}
                    isFirst={i === 0}
                    isLast={i === sortedLessons.length - 1}
                  />
                  <span className={`rounded px-2 py-0.5 text-xs ${
                    l.type === 'card' ? 'bg-brand-500/20 text-brand-700'
                    : l.type === 'quiz' ? 'bg-success-500/20 text-success-600'
                    : 'bg-accent-500/20 text-accent-500'
                  }`}>{l.type}</span>
                  <span className="flex-1 truncate text-sm text-ink">
                    {lessonLabel(l)}
                  </span>
                  <span className="text-xs text-muted-foreground">{l.xp_reward} XP</span>
                  <button type="button" onClick={() => { setEditingLesson(l); setShowNewLesson(false); }}
                    className="text-xs text-brand-600">Edit</button>
                  <button type="button" onClick={() => setDeleteTarget(l)}
                    className="text-xs text-danger-500">Delete</button>
                </div>
              ))}
            </div>
            <ModuleEngagement moduleId={moduleId} />
          </div>
        )}

        <div className="mt-4 flex gap-3">
          <button type="submit" className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700">
            Save
          </button>
          <button type="button" onClick={() => navigate('/admin/modules')}
            className="rounded-md border border-line px-6 py-2 text-sm text-muted-foreground hover:bg-brand-50">
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
