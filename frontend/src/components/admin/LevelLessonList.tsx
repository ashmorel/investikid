import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useLevelLessons, useDeleteLesson, lessonLabel } from '@/api/admin';
import type { AdminLesson } from '@/api/admin';
import LessonForm from './LessonForm';
import ConfirmDialog from './ConfirmDialog';
import LessonDraftReview from './LessonDraftReview';

export default function LevelLessonList() {
  const { t } = useTranslation('admin');
  const { moduleId = '', levelId = '' } = useParams<{ moduleId: string; levelId: string }>();
  const { data: lessons = [], isLoading } = useLevelLessons(levelId);
  const deleteLesson = useDeleteLesson();

  const [editingLesson, setEditingLesson] = useState<AdminLesson | null>(null);
  const [showNewLesson, setShowNewLesson] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminLesson | null>(null);

  const sorted = [...lessons].sort((a, b) => a.order_index - b.order_index);

  if (isLoading) return <p className="text-muted-foreground">{t('levelLessonList.loading')}</p>;

  return (
    <div>
      <div className="mb-2">
        <Link to={`/admin/modules/${moduleId}/levels`} className="text-xs text-muted-foreground hover:text-ink">
          {t('levelLessonList.backToLevels')}
        </Link>
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-ink">{t('levelLessonList.heading')}</h2>
        <button
          type="button"
          onClick={() => { setEditingLesson(null); setShowNewLesson(true); }}
          className="text-sm text-brand-600 hover:text-brand-700"
        >
          {t('levelLessonList.addLesson')}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {sorted.map((lesson) => (
          <div key={lesson.id} className="flex items-center gap-2 rounded-md border border-line bg-card px-3 py-2">
            <span className={`rounded px-2 py-0.5 text-xs ${
              lesson.type === 'card' ? 'bg-brand-100 text-brand-700'
              : lesson.type === 'quiz' ? 'bg-success-500/20 text-success-600'
              : 'bg-accent-500/20 text-accent-500'
            }`}>{lesson.type}</span>
            <span className="flex-1 truncate text-sm text-ink">
              {lessonLabel(lesson)}
            </span>
            <span className="text-xs text-muted-foreground">{lesson.xp_reward} XP</span>
            <button
              type="button"
              onClick={() => { setEditingLesson(lesson); setShowNewLesson(false); }}
              className="text-xs text-brand-600"
            >
              {t('levelLessonList.edit')}
            </button>
            <button
              type="button"
              onClick={() => setDeleteTarget(lesson)}
              className="text-xs text-danger-500"
            >
              {t('levelLessonList.delete')}
            </button>
          </div>
        ))}
      </div>

      {(editingLesson || showNewLesson) && (
        <LessonForm
          moduleId={moduleId}
          levelId={levelId}
          lesson={editingLesson ?? undefined}
          nextOrderIndex={sorted.length}
          onClose={() => { setEditingLesson(null); setShowNewLesson(false); }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title={t('levelLessonList.deleteTitle')}
        message={t('levelLessonList.deleteMessage')}
        onConfirm={() => { if (deleteTarget) deleteLesson.mutate(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />

      <LessonDraftReview levelId={levelId} />
    </div>
  );
}
