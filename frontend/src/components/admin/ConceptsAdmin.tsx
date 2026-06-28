import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useConcepts,
  useCreateConcept,
  usePatchConcept,
  type ConceptOut,
  type ConceptIn,
  type ConceptPatch,
} from '@/api/adminConcepts';
import { FormSection } from '@/components/admin/FormSection';

const TOPICS = [
  'stocks', 'savings', 'real_estate', 'budgeting', 'risk',
  'crypto', 'taxes', 'debt', 'entrepreneurship',
] as const;

type Tier = 1 | 2 | 3;

interface FormState {
  topic: string;
  slug: string;
  name: string;
  blurb: string;
  difficulty_tier: Tier;
  order_index: number;
}

const EMPTY_FORM: FormState = {
  topic: 'stocks',
  slug: '',
  name: '',
  blurb: '',
  difficulty_tier: 1,
  order_index: 0,
};

export default function ConceptsAdmin() {
  const { t } = useTranslation('admin');
  const { data: overview, isLoading } = useConcepts();
  const groups = overview?.groups ?? [];
  const unmappedLessons = overview?.unmapped_lessons ?? 0;
  const create = useCreateConcept();
  const patch = usePatchConcept();

  const [editing, setEditing] = useState<ConceptOut | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [error, setError] = useState('');

  function startCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setError('');
  }

  function startEdit(c: ConceptOut) {
    setEditing(c);
    setForm({
      topic: c.topic,
      slug: c.slug,
      name: c.name,
      blurb: c.blurb ?? '',
      difficulty_tier: c.difficulty_tier,
      order_index: c.order_index,
    });
    setError('');
  }

  function cancelForm() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setError('');
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      if (editing) {
        const body: ConceptPatch = {
          topic: form.topic,
          slug: form.slug || undefined,
          name: form.name,
          blurb: form.blurb || null,
          difficulty_tier: form.difficulty_tier,
          order_index: form.order_index,
        };
        await patch.mutateAsync({ id: editing.id, body });
      } else {
        const body: ConceptIn = {
          topic: form.topic,
          slug: form.slug,
          name: form.name,
          blurb: form.blurb || null,
          difficulty_tier: form.difficulty_tier,
          order_index: form.order_index,
        };
        await create.mutateAsync(body);
      }
      cancelForm();
    } catch {
      setError(t('concepts.saveError'));
    }
  }

  const inputCls =
    'rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 min-h-[44px]';

  return (
    <div className="max-w-3xl space-y-6">
      <h2 className="text-xl font-semibold text-ink">{t('concepts.title')}</h2>

      {isLoading && <p className="text-sm text-muted-foreground">{t('concepts.loading')}</p>}

      {/* Global unmapped lessons banner */}
      {!isLoading && (
        <p className="text-sm text-muted-foreground">
          {t('concepts.unmappedTotal', { count: unmappedLessons })}
        </p>
      )}

      {/* Topic-grouped concept list */}
      {groups.map((group) => (
        <section key={group.topic} aria-labelledby={`topic-${group.topic}`}>
          <div className="mb-2 flex items-center gap-3">
            <h3
              id={`topic-${group.topic}`}
              className="text-sm font-bold uppercase tracking-wide text-muted-foreground"
            >
              {group.topic}
            </h3>
          </div>
          {group.concepts.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('concepts.noConcepts')}</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line bg-muted/50 text-left">
                    <th className="px-3 py-2">{t('concepts.colName')}</th>
                    <th className="px-3 py-2">{t('concepts.colSlug')}</th>
                    <th className="px-3 py-2">{t('concepts.colTier')}</th>
                    <th className="px-3 py-2">{t('concepts.colLessons')}</th>
                    <th className="px-3 py-2">
                      <span className="sr-only">{t('concepts.colActions')}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {group.concepts.map((c) => (
                    <tr key={c.id} className="border-b last:border-b-0 hover:bg-muted/50">
                      <td className="px-3 py-2 font-medium">{c.name}</td>
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{c.slug}</td>
                      <td className="px-3 py-2">{c.difficulty_tier}</td>
                      <td className="px-3 py-2">{c.lesson_count}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          type="button"
                          className="text-sm font-bold text-brand-700 min-h-[44px] px-2"
                          onClick={() => startEdit(c)}
                        >
                          {t('concepts.edit')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}

      {/* Create / Edit form */}
      <FormSection
        title={editing ? t('concepts.editHeading') : t('concepts.createHeading')}
        helper={editing ? t('concepts.editHelper', { name: editing.name }) : undefined}
      >
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            {t('concepts.topicLabel')}
            <select
              className={inputCls}
              value={form.topic}
              onChange={(e) => setForm((f) => ({ ...f, topic: e.target.value }))}
              required
            >
              {TOPICS.map((tp) => (
                <option key={tp} value={tp}>
                  {tp}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('concepts.slugLabel')}
            <input
              type="text"
              className={inputCls}
              value={form.slug}
              onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
              placeholder="e.g. stocks-what-is-a-share"
              required={!editing}
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('concepts.nameLabel')}
            <input
              type="text"
              className={inputCls}
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('concepts.blurbLabel')}
            <textarea
              className="rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
              rows={2}
              value={form.blurb}
              onChange={(e) => setForm((f) => ({ ...f, blurb: e.target.value }))}
            />
          </label>

          <div className="flex gap-4">
            <label className="flex flex-col gap-1 text-sm">
              {t('concepts.tierLabel')}
              <select
                className={inputCls}
                value={form.difficulty_tier}
                onChange={(e) =>
                  setForm((f) => ({ ...f, difficulty_tier: Number(e.target.value) as Tier }))
                }
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              {t('concepts.orderLabel')}
              <input
                type="number"
                min={0}
                className={inputCls}
                value={form.order_index}
                onChange={(e) => setForm((f) => ({ ...f, order_index: Number(e.target.value) }))}
              />
            </label>
          </div>

          {error && <p role="alert" className="text-sm text-danger-700">{error}</p>}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={create.isPending || patch.isPending}
              className="min-h-[44px] rounded-md bg-brand-600 px-4 font-bold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {t('concepts.save')}
            </button>
            {editing && (
              <button
                type="button"
                onClick={cancelForm}
                className="min-h-[44px] rounded-md border border-line px-4 font-bold hover:bg-muted"
              >
                {t('concepts.cancel')}
              </button>
            )}
            {!editing && (
              <button
                type="button"
                onClick={startCreate}
                className="min-h-[44px] rounded-md border border-line px-4 font-bold hover:bg-muted"
              >
                {t('concepts.reset')}
              </button>
            )}
          </div>
        </form>
      </FormSection>
    </div>
  );
}
