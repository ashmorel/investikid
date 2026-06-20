import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useLevelDrafts,
  useLevelLessons,
  useGenerateLevelLessons,
  useApproveDraft,
  useApproveDrafts,
  useUpdateDraft,
  useRegenerateDraft,
  useRejectDraft,
} from '@/api/admin';
import type { LessonDraft } from '@/api/admin';
import ConfirmDialog from './ConfirmDialog';

const TYPE_BADGE: Record<LessonDraft['type'], string> = {
  card: 'bg-brand-100 text-brand-700',
  quiz: 'bg-success-500/20 text-success-600',
  scenario: 'bg-accent-500/20 text-accent-500',
};

function DraftPreview({ draft }: { draft: LessonDraft }) {
  const cj = draft.content_json;
  if (draft.type === 'card') {
    return (
      <div className="text-sm text-ink">
        <p className="font-medium">{String(cj.title ?? '')}</p>
        <p className="text-muted-foreground">{String(cj.body ?? '')}</p>
      </div>
    );
  }
  if (draft.type === 'quiz') {
    const choices = Array.isArray(cj.choices) ? (cj.choices as string[]) : [];
    const answerIndex = typeof cj.answer_index === 'number' ? cj.answer_index : -1;
    return (
      <div className="text-sm text-ink">
        <p className="font-medium">{String(cj.question ?? '')}</p>
        <ul className="mt-1 list-disc pl-5">
          {choices.map((c, i) => (
            <li key={i} className={i === answerIndex ? 'font-semibold text-success-600' : 'text-muted-foreground'}>
              {c}
              {i === answerIndex ? ' ✓' : ''}
            </li>
          ))}
        </ul>
      </div>
    );
  }
  // scenario
  const choices = Array.isArray(cj.choices) ? (cj.choices as { label: string; outcome: string }[]) : [];
  const correctIndex = typeof cj.correct_index === 'number' ? cj.correct_index : -1;
  return (
    <div className="text-sm text-ink">
      <p className="font-medium">{String(cj.prompt ?? '')}</p>
      <ul className="mt-1 list-disc pl-5">
        {choices.map((c, i) => (
          <li key={i} className={i === correctIndex ? 'font-semibold text-success-600' : 'text-muted-foreground'}>
            {c.label}
            {c.outcome ? ` — ${c.outcome}` : ''}
            {i === correctIndex ? ' ✓' : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface DraftCardProps {
  draft: LessonDraft;
  onApprove: (id: string) => void;
  onRegenerate: (id: string) => void;
  onReject: (draft: LessonDraft) => void;
  onSaveEdit: (id: string, content_json: Record<string, unknown>) => void;
}

function DraftCard({ draft, onApprove, onRegenerate, onReject, onSaveEdit }: DraftCardProps) {
  const { t } = useTranslation('admin');
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');

  function startEdit() {
    setEditText(JSON.stringify(draft.content_json, null, 2));
    setEditing(true);
  }

  function saveEdit() {
    try {
      const parsed = JSON.parse(editText) as Record<string, unknown>;
      onSaveEdit(draft.id, parsed);
      setEditing(false);
    } catch {
      // Invalid JSON — keep the editor open so the admin can fix it.
    }
  }

  const editFieldId = `draft-edit-${draft.id}`;

  return (
    <div data-testid={`draft-${draft.id}`} className="rounded-md border border-line bg-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs capitalize ${TYPE_BADGE[draft.type]}`}>{draft.type}</span>
        {draft.moderation_safe ? (
          <span className="rounded bg-success-100 px-2 py-0.5 text-xs text-success-800">{t('draftReview.draft.safe')}</span>
        ) : (
          <span className="rounded bg-danger-100 px-2 py-0.5 text-xs text-danger-700">
            {t('draftReview.draft.flagged', { category: draft.moderation_category })}
          </span>
        )}
        {draft.adaptation_flags?.suspect && (
          <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-900" role="status">
            {t('draftReview.adaptation.suspect', { terms: draft.adaptation_flags.uk_residue.join(', ') })}
          </span>
        )}
      </div>

      {editing ? (
        <div>
          <label htmlFor={editFieldId} className="mb-1 block text-sm text-ink">
            {t('draftReview.draft.editLabel')}
          </label>
          <textarea
            id={editFieldId}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            rows={8}
            className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-ink focus:ring-2 focus:ring-brand-300"
          />
        </div>
      ) : (
        <DraftPreview draft={draft} />
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {editing ? (
          <>
            <button
              type="button"
              onClick={saveEdit}
              className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700"
            >
              {t('draftReview.draft.save')}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-muted-foreground hover:bg-brand-50"
            >
              {t('draftReview.draft.cancel')}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              onClick={() => onApprove(draft.id)}
              disabled={!draft.moderation_safe}
              title={draft.moderation_safe ? t('draftReview.draft.approveTitle') : t('draftReview.draft.approveTitleBlocked')}
              aria-label={draft.moderation_safe ? t('draftReview.draft.approveLabel') : t('draftReview.draft.approveLabelBlocked')}
              className="min-h-[44px] rounded-md bg-success-600 px-4 py-2 text-sm text-white hover:bg-success-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('draftReview.draft.approveButton')}
            </button>
            <button
              type="button"
              onClick={startEdit}
              className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-brand-600 hover:bg-brand-50"
            >
              {t('draftReview.draft.editButton')}
            </button>
            <button
              type="button"
              onClick={() => onRegenerate(draft.id)}
              className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50"
            >
              {t('draftReview.draft.regenerateButton')}
            </button>
            <button
              type="button"
              onClick={() => onReject(draft)}
              className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-danger-500 hover:bg-danger-100"
            >
              {t('draftReview.draft.rejectButton')}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

interface LessonDraftReviewProps {
  levelId: string;
}

export default function LessonDraftReview({ levelId }: LessonDraftReviewProps) {
  const { t } = useTranslation('admin');
  const { data: drafts = [], isLoading } = useLevelDrafts(levelId);
  const { data: lessons = [] } = useLevelLessons(levelId);
  const publishedCount = lessons.length;
  const generate = useGenerateLevelLessons(levelId);
  const approve = useApproveDraft(levelId);
  const approveDrafts = useApproveDrafts(levelId);
  const update = useUpdateDraft(levelId);
  const regenerate = useRegenerateDraft(levelId);
  const reject = useRejectDraft(levelId);

  const [concept, setConcept] = useState('');
  const [count, setCount] = useState(3);
  const [types, setTypes] = useState<Record<LessonDraft['type'], boolean>>({
    card: true,
    quiz: false,
    scenario: false,
  });
  const [rejectTarget, setRejectTarget] = useState<LessonDraft | null>(null);
  const [confirmReplace, setConfirmReplace] = useState(false);

  function toggleType(t: LessonDraft['type']) {
    setTypes((prev) => ({ ...prev, [t]: !prev[t] }));
  }

  function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    const selected = (Object.keys(types) as LessonDraft['type'][]).filter((t) => types[t]);
    generate.mutate({ concept, count, types: selected });
  }

  const skipped = generate.data?.skipped ?? 0;

  return (
    <section className="mt-8 border-t border-line pt-6">
      <h2 className="mb-4 text-xl font-semibold text-ink">{t('draftReview.generateHeading')}</h2>

      <form onSubmit={handleGenerate} className="mb-6 flex flex-col gap-4">
        <div>
          <label htmlFor="gen-concept" className="mb-1 block text-sm text-ink">
            {t('draftReview.conceptLabel')}
          </label>
          <input
            id="gen-concept"
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            required
            className="w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300"
          />
        </div>

        <div>
          <label htmlFor="gen-count" className="mb-1 block text-sm text-ink">
            {t('draftReview.countLabel')}
          </label>
          <input
            id="gen-count"
            type="number"
            min={1}
            max={8}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-24 rounded-md border border-input bg-background px-3 py-2 text-base text-ink focus:ring-2 focus:ring-brand-300"
          />
        </div>

        <fieldset>
          <legend className="mb-1 block text-sm text-ink">{t('draftReview.lessonTypesLabel')}</legend>
          <div className="flex flex-wrap gap-4">
            {(['card', 'quiz', 'scenario'] as const).map((t) => (
              <label key={t} className="flex items-center gap-2 text-sm capitalize text-ink">
                <input
                  type="checkbox"
                  checked={types[t]}
                  onChange={() => toggleType(t)}
                  className="h-4 w-4 rounded border-input bg-background"
                />
                {t}
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <button
            type="submit"
            disabled={generate.isPending}
            className="min-h-[44px] rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {generate.isPending ? t('draftReview.generating') : t('draftReview.generateButton')}
          </button>
        </div>

        {generate.isPending && (
          <p role="status" className="text-sm text-muted-foreground">
            {t('draftReview.generatingStatus')}
          </p>
        )}
        {skipped > 0 && (
          <p className="text-sm text-danger-600">
            {t('draftReview.skipped', { count: skipped })}
          </p>
        )}
      </form>

      <h3 className="mb-3 text-lg font-semibold text-ink">{t('draftReview.draftReviewHeading')}</h3>

      {isLoading ? (
        <p className="text-muted-foreground">{t('draftReview.loadingDrafts')}</p>
      ) : drafts.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('draftReview.noDrafts')}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => approveDrafts.mutate(false)}
              disabled={approveDrafts.isPending}
              className="min-h-[44px] rounded-md bg-success-600 px-4 py-2 text-sm text-white hover:bg-success-500 disabled:opacity-50"
            >
              {t('draftReview.approveAll')}
            </button>
            {publishedCount > 0 && (
              <button
                type="button"
                onClick={() => setConfirmReplace(true)}
                disabled={approveDrafts.isPending}
                className="min-h-[44px] rounded-md bg-danger-600 px-4 py-2 text-sm text-white hover:bg-danger-500 disabled:opacity-50"
              >
                {t('draftReview.publishReplace', { count: publishedCount })}
              </button>
            )}
          </div>
          {approveDrafts.isSuccess && approveDrafts.data && (
            <p role="status" className="text-sm text-success-700">
              {t('draftReview.approveResult', {
                approved: approveDrafts.data.approved,
                replaced: approveDrafts.data.replaced,
                skipped: approveDrafts.data.skipped_unsafe,
              })}
            </p>
          )}
          {drafts.map((draft) => (
            <DraftCard
              key={draft.id}
              draft={draft}
              onApprove={(id) => approve.mutate(id)}
              onRegenerate={(id) => regenerate.mutate(id)}
              onReject={(d) => setRejectTarget(d)}
              onSaveEdit={(id, content_json) => update.mutate({ id, content_json })}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!rejectTarget}
        title={t('draftReview.rejectTitle')}
        message={t('draftReview.rejectMessage')}
        onConfirm={() => {
          if (rejectTarget) reject.mutate(rejectTarget.id);
          setRejectTarget(null);
        }}
        onCancel={() => setRejectTarget(null)}
      />

      <ConfirmDialog
        open={confirmReplace}
        title={t('draftReview.replaceConfirmTitle')}
        message={t('draftReview.replaceConfirmMessage', { count: publishedCount })}
        onConfirm={() => {
          approveDrafts.mutate(true);
          setConfirmReplace(false);
        }}
        onCancel={() => setConfirmReplace(false)}
      />
    </section>
  );
}
