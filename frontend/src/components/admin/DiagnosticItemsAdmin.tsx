import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useDiagnosticItems,
  useGenerateItems,
  usePatchItem,
  useApproveItem,
  useRejectItem,
  useRetireItem,
  useUnpublishItem,
  useVerifyItems,
  type DiagnosticItem,
  type DiagnosticItemPatch,
  type DiagnosticFilters,
  type VerifyResult,
} from '@/api/adminDiagnostic';
import { FormSection } from '@/components/admin/FormSection';

const TOPICS = [
  'stocks', 'savings', 'real_estate', 'budgeting', 'risk',
  'crypto', 'taxes', 'debt', 'entrepreneurship',
] as const;

type Tier = 1 | 2 | 3;
type ItemStatus = DiagnosticItem['status'];

const STATUS_OPTIONS: ItemStatus[] = ['draft', 'approved', 'retired'];

const inputCls =
  'rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 min-h-[44px]';

function statusChipCls(status: ItemStatus): string {
  switch (status) {
    case 'approved':
      return 'inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-bold text-green-800';
    case 'retired':
      return 'inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-bold text-zinc-600';
    default:
      return 'inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800';
  }
}

function StatusChip({ status }: { status: ItemStatus }) {
  const { t } = useTranslation('admin');
  const key = `diagnosticItems.status${status.charAt(0).toUpperCase()}${status.slice(1)}` as const;
  return <span className={statusChipCls(status)}>{t(key)}</span>;
}

function VerifierBadge({ item }: { item: DiagnosticItem }) {
  const { t } = useTranslation('admin');
  const { verifier_status, verifier_answer_index, verifier_note, answer_index, id } = item;

  if (verifier_status === 'mismatch' || verifier_status === 'ambiguous') {
    return (
      <div
        data-testid={`verifier-warning-${id}`}
        className="rounded-md border border-amber-400 bg-amber-50 px-3 py-2 text-sm text-amber-900"
      >
        <p className="font-bold">{t('diagnosticItems.verifierWarningTitle')}</p>
        <p>{t('diagnosticItems.verifierDeclared', { index: answer_index })}</p>
        <p>{t('diagnosticItems.verifierSuggested', { index: verifier_answer_index ?? '—' })}</p>
        {verifier_note && (
          <p>{t('diagnosticItems.verifierNote', { note: verifier_note })}</p>
        )}
      </div>
    );
  }

  if (verifier_status === 'agree') {
    return (
      <span
        data-testid={`verifier-agree-${id}`}
        className="inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700"
      >
        {t('diagnosticItems.verifierAgree')}
      </span>
    );
  }

  return null;
}

function coverageCellText(count: number, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (count === 0) return t('diagnosticItems.coverageNone');
  if (count >= 2) return t('diagnosticItems.coverageMet', { count });
  return t('diagnosticItems.coverageShort', { count });
}

function coverageCellCls(count: number): string {
  if (count === 0) return 'bg-red-50 text-red-700 text-xs px-2 py-1 text-center';
  if (count >= 2) return 'bg-green-50 text-green-800 text-xs px-2 py-1 text-center';
  return 'bg-amber-50 text-amber-800 text-xs px-2 py-1 text-center';
}

interface EditState {
  question: string;
  choices: string;
  answerIndex: number;
  explanation: string;
  tier: Tier;
}

function itemToEditState(item: DiagnosticItem): EditState {
  return {
    question: item.question,
    choices: item.choices.join('\n'),
    answerIndex: item.answer_index,
    explanation: item.explanation,
    tier: item.difficulty_tier,
  };
}

export default function DiagnosticItemsAdmin() {
  const { t } = useTranslation('admin');

  const [filters, setFilters] = useState<DiagnosticFilters>({
    market_code: '',
    topic: '',
    status: '',
    verifier: '',
  });

  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [verifyError, setVerifyError] = useState('');

  const [genMarket, setGenMarket] = useState('GB');
  const [genTopic, setGenTopic] = useState<string>(TOPICS[0]);
  const [genTier, setGenTier] = useState<Tier>(1);
  const [genCount, setGenCount] = useState(5);
  const [genError, setGenError] = useState('');

  const [editingItem, setEditingItem] = useState<DiagnosticItem | null>(null);
  const [editForm, setEditForm] = useState<EditState | null>(null);
  const [saveError, setSaveError] = useState('');
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});

  const { data, isLoading } = useDiagnosticItems(filters);
  const items = data?.items ?? [];
  const coverage = data?.coverage ?? [];

  const generate = useGenerateItems();
  const patch = usePatchItem();
  const approve = useApproveItem();
  const reject = useRejectItem();
  const retire = useRetireItem();
  const unpublish = useUnpublishItem();
  const verify = useVerifyItems();

  // Group items by topic
  const topicGroups = TOPICS.reduce<Record<string, DiagnosticItem[]>>((acc, topic) => {
    acc[topic] = items.filter((item) => item.topic === topic);
    return acc;
  }, {});

  // Build coverage lookup: topic + tier → count
  const coverageMap = coverage.reduce<Record<string, number>>((acc, cell) => {
    acc[`${cell.topic}:${cell.difficulty_tier}`] = cell.approved_count;
    return acc;
  }, {});

  // Always render the full grid — the backend only returns rows with approved items (GROUP BY omits zeros)
  const topicsWithCoverage = TOPICS;

  async function onGenerate(e: React.FormEvent) {
    e.preventDefault();
    setGenError('');
    try {
      await generate.mutateAsync({
        market_code: genMarket,
        topic: genTopic,
        difficulty_tier: genTier,
        count: genCount,
      });
    } catch {
      setGenError(t('diagnosticItems.generateError'));
    }
  }

  function startEdit(item: DiagnosticItem) {
    setEditingItem(item);
    setEditForm(itemToEditState(item));
    setSaveError('');
  }

  function cancelEdit() {
    setEditingItem(null);
    setEditForm(null);
    setSaveError('');
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!editingItem || !editForm) return;
    setSaveError('');
    try {
      const body: DiagnosticItemPatch = {
        question: editForm.question,
        choices: editForm.choices.split('\n').map((c) => c.trim()).filter(Boolean),
        answer_index: editForm.answerIndex,
        explanation: editForm.explanation,
        difficulty_tier: editForm.tier,
      };
      await patch.mutateAsync({ id: editingItem.id, body });
      cancelEdit();
    } catch {
      setSaveError(t('diagnosticItems.saveError'));
    }
  }

  async function onVerifyAll() {
    setVerifyError('');
    setVerifyResult(null);
    try {
      const result = await verify.mutateAsync({
        market_code: filters.market_code || undefined,
        topic: filters.topic || undefined,
        status: filters.status || undefined,
      });
      setVerifyResult(result);
    } catch {
      setVerifyError(t('diagnosticItems.verifyError'));
    }
  }

  return (
    <div className="max-w-4xl space-y-8">
      <h2 className="text-xl font-semibold text-ink">{t('diagnosticItems.title')}</h2>

      {isLoading && (
        <p className="text-sm text-muted-foreground">{t('diagnosticItems.loading')}</p>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1 text-sm">
          {t('diagnosticItems.marketLabel')}
          <input
            type="text"
            className={inputCls}
            value={filters.market_code ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, market_code: e.target.value }))}
            placeholder="e.g. GB"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          {t('diagnosticItems.topicLabel')}
          <select
            className={inputCls}
            value={filters.topic ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, topic: e.target.value }))}
          >
            <option value="">{t('diagnosticItems.allTopics')}</option>
            {TOPICS.map((tp) => (
              <option key={tp} value={tp}>{tp}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 text-sm">
          {t('diagnosticItems.statusLabel')}
          <select
            className={inputCls}
            value={filters.status ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">{t('diagnosticItems.allStatuses')}</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {t(`diagnosticItems.status${s.charAt(0).toUpperCase()}${s.slice(1)}`)}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-end gap-2">
          <button
            type="button"
            className={`min-h-[44px] rounded-md border px-3 text-sm font-bold ${
              filters.verifier === 'needs_review'
                ? 'border-amber-500 bg-amber-100 text-amber-900 hover:bg-amber-200'
                : 'border-line hover:bg-muted'
            }`}
            onClick={() =>
              setFilters((f) => ({
                ...f,
                verifier: f.verifier === 'needs_review' ? '' : 'needs_review',
              }))
            }
          >
            {filters.verifier === 'needs_review'
              ? t('diagnosticItems.needsReviewFilterActive')
              : t('diagnosticItems.needsReviewFilter')}
          </button>

          <button
            type="button"
            disabled={verify.isPending}
            className="min-h-[44px] rounded-md border border-line bg-background px-3 text-sm font-bold hover:bg-muted disabled:opacity-50"
            onClick={onVerifyAll}
          >
            {verify.isPending
              ? t('diagnosticItems.verifying')
              : t('diagnosticItems.verifyAll')}
          </button>
        </div>
      </div>

      {verifyResult && (
        <div
          data-testid="verify-all-result"
          className="rounded-md border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-900"
        >
          {t('diagnosticItems.verifyResultSummary', {
            verified: verifyResult.verified,
            agree: verifyResult.agree,
            mismatch: verifyResult.mismatch,
            ambiguous: verifyResult.ambiguous,
            error: verifyResult.error,
          })}
        </div>
      )}

      {verifyError && (
        <p role="alert" className="text-sm text-danger-700">{verifyError}</p>
      )}

      {/* Generate section */}
      <FormSection title={t('diagnosticItems.generateHeading')}>
        <form onSubmit={onGenerate} className="flex flex-wrap gap-3 items-end">
          <label className="flex flex-col gap-1 text-sm">
            {t('diagnosticItems.marketLabel')}
            <input
              type="text"
              className={inputCls}
              value={genMarket}
              onChange={(e) => setGenMarket(e.target.value)}
              placeholder="GB"
              required
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('diagnosticItems.generateTopicLabel')}
            <select
              className={inputCls}
              value={genTopic}
              onChange={(e) => setGenTopic(e.target.value)}
            >
              {TOPICS.map((tp) => (
                <option key={tp} value={tp}>{tp}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('diagnosticItems.generateTierLabel')}
            <select
              className={inputCls}
              value={genTier}
              onChange={(e) => setGenTier(Number(e.target.value) as Tier)}
            >
              <option value={1}>{t('diagnosticItems.tier1')}</option>
              <option value={2}>{t('diagnosticItems.tier2')}</option>
              <option value={3}>{t('diagnosticItems.tier3')}</option>
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            {t('diagnosticItems.generateCountLabel')}
            <input
              type="number"
              min={1}
              max={20}
              className={inputCls}
              value={genCount}
              onChange={(e) => setGenCount(Number(e.target.value))}
              required
            />
          </label>

          <div className="flex flex-col gap-1">
            <span className="text-sm opacity-0" aria-hidden="true">.</span>
            <button
              type="submit"
              disabled={generate.isPending}
              className="min-h-[44px] rounded-md bg-brand-600 px-4 font-bold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {generate.isPending
                ? t('diagnosticItems.generating')
                : t('diagnosticItems.generateButton')}
            </button>
          </div>

          {genError && (
            <p role="alert" className="w-full text-sm text-danger-700">{genError}</p>
          )}
        </form>
      </FormSection>

      {/* Coverage table — always show the full 9×3 grid when any coverage data exists */}
      {coverage.length > 0 && (
        <section aria-labelledby="coverage-heading">
          <h3
            id="coverage-heading"
            className="mb-2 text-sm font-bold text-muted-foreground"
          >
            {t('diagnosticItems.coverageHeading')}
          </h3>
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-muted/50 text-left">
                  <th className="px-3 py-2">{t('diagnosticItems.topicLabel')}</th>
                  <th className="px-3 py-2 text-center">{t('diagnosticItems.tier1')}</th>
                  <th className="px-3 py-2 text-center">{t('diagnosticItems.tier2')}</th>
                  <th className="px-3 py-2 text-center">{t('diagnosticItems.tier3')}</th>
                </tr>
              </thead>
              <tbody>
                {topicsWithCoverage.map((topic) => (
                  <tr key={topic} className="border-b last:border-b-0">
                    <td className="px-3 py-2 font-medium">{topic}</td>
                    {([1, 2, 3] as Tier[]).map((tier) => {
                      const count = coverageMap[`${topic}:${tier}`] ?? 0;
                      return (
                        <td key={tier} className={coverageCellCls(count)}>
                          {coverageCellText(count, t)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Items grouped by topic */}
      {items.length === 0 && !isLoading && (
        <p className="text-sm text-muted-foreground">{t('diagnosticItems.noItems')}</p>
      )}

      {TOPICS.map((topic) => {
        const group = topicGroups[topic] ?? [];
        if (group.length === 0) return null;
        return (
          <section key={topic} aria-labelledby={`diag-topic-${topic}`}>
            <h3
              id={`diag-topic-${topic}`}
              className="mb-2 text-sm font-bold uppercase tracking-wide text-muted-foreground"
            >
              {topic}
            </h3>

            <div className="space-y-4">
              {group.map((item) => (
                <div
                  key={item.id}
                  className="rounded-lg border border-line bg-card p-4 space-y-2"
                >
                  {/* Header row */}
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusChip status={item.status} />
                    <span className="text-xs text-muted-foreground">
                      {t(`diagnosticItems.tier${item.difficulty_tier}`)}
                    </span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {t('diagnosticItems.colSource')}: {item.source}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {item.times_shown}/{item.times_correct}
                    </span>
                  </div>

                  {/* Verifier badge / warning */}
                  <VerifierBadge item={item} />

                  {/* Question */}
                  <p className="font-medium text-ink">{item.question}</p>

                  {/* Choices */}
                  <ol className="ml-4 space-y-0.5">
                    {item.choices.map((choice, idx) => (
                      <li
                        key={idx}
                        className={
                          idx === item.answer_index
                            ? 'font-bold text-brand-700'
                            : 'text-sm text-ink'
                        }
                      >
                        {choice}
                        {idx === item.answer_index && (
                          <span className="ml-1 text-xs font-bold text-brand-700">
                            {t('diagnosticItems.correctChoice')}
                          </span>
                        )}
                      </li>
                    ))}
                  </ol>

                  {/* Explanation */}
                  <p className="text-sm text-muted-foreground">{item.explanation}</p>

                  {/* Actions */}
                  <div className="flex flex-wrap gap-2 pt-1">
                    {item.status === 'draft' && (
                      <button
                        type="button"
                        className="min-h-[44px] rounded-md bg-green-600 px-3 text-sm font-bold text-white hover:bg-green-700"
                        onClick={async () => {
                          setActionErrors((prev) => { const next = { ...prev }; delete next[item.id]; return next; });
                          try {
                            await approve.mutateAsync(item.id);
                          } catch {
                            setActionErrors((prev) => ({ ...prev, [item.id]: t('diagnosticItems.actionError') }));
                          }
                        }}
                      >
                        {t('diagnosticItems.approve')}
                      </button>
                    )}
                    {(item.status === 'draft' || item.status === 'approved') && (
                      <button
                        type="button"
                        className="min-h-[44px] rounded-md bg-red-600 px-3 text-sm font-bold text-white hover:bg-red-700"
                        onClick={async () => {
                          setActionErrors((prev) => { const next = { ...prev }; delete next[item.id]; return next; });
                          try {
                            await reject.mutateAsync(item.id);
                          } catch {
                            setActionErrors((prev) => ({ ...prev, [item.id]: t('diagnosticItems.actionError') }));
                          }
                        }}
                      >
                        {t('diagnosticItems.reject')}
                      </button>
                    )}
                    {item.status === 'approved' && (
                      <button
                        type="button"
                        className="min-h-[44px] rounded-md border border-line px-3 text-sm font-bold hover:bg-muted"
                        onClick={async () => {
                          setActionErrors((prev) => { const next = { ...prev }; delete next[item.id]; return next; });
                          try {
                            await retire.mutateAsync(item.id);
                          } catch {
                            setActionErrors((prev) => ({ ...prev, [item.id]: t('diagnosticItems.actionError') }));
                          }
                        }}
                      >
                        {t('diagnosticItems.retire')}
                      </button>
                    )}
                    {item.status === 'approved' && (
                      <button
                        type="button"
                        className="min-h-[44px] rounded-md border border-amber-400 px-3 text-sm font-bold text-amber-800 hover:bg-amber-50"
                        onClick={async () => {
                          setActionErrors((prev) => { const next = { ...prev }; delete next[item.id]; return next; });
                          try {
                            await unpublish.mutateAsync(item.id);
                          } catch {
                            setActionErrors((prev) => ({ ...prev, [item.id]: t('diagnosticItems.actionError') }));
                          }
                        }}
                      >
                        {t('diagnosticItems.unpublishToEdit')}
                      </button>
                    )}
                    {item.status === 'draft' && (
                      <button
                        type="button"
                        className="min-h-[44px] rounded-md border border-line px-3 text-sm font-bold text-brand-700 hover:bg-brand-50"
                        onClick={() => startEdit(item)}
                      >
                        {t('diagnosticItems.edit')}
                      </button>
                    )}
                  </div>

                  {actionErrors[item.id] && (
                    <p role="alert" className="text-sm text-danger-700">{actionErrors[item.id]}</p>
                  )}

                  {/* Inline edit panel (draft only) */}
                  {editingItem?.id === item.id && editForm && (
                    <FormSection
                      title={t('diagnosticItems.editHeading')}
                      helper={t('diagnosticItems.editHelper')}
                    >
                      <form onSubmit={onSave} className="flex flex-col gap-4">
                        <label className="flex flex-col gap-1 text-sm">
                          {t('diagnosticItems.questionLabel')}
                          <textarea
                            rows={3}
                            className="rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
                            value={editForm.question}
                            onChange={(e) =>
                              setEditForm((f) => f ? { ...f, question: e.target.value } : f)
                            }
                            required
                          />
                        </label>

                        <label className="flex flex-col gap-1 text-sm">
                          {t('diagnosticItems.choicesLabel')}
                          <textarea
                            rows={4}
                            className="rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
                            value={editForm.choices}
                            onChange={(e) =>
                              setEditForm((f) => f ? { ...f, choices: e.target.value } : f)
                            }
                          />
                        </label>

                        <label className="flex flex-col gap-1 text-sm">
                          {t('diagnosticItems.answerIndexLabel')}
                          <input
                            type="number"
                            min={0}
                            className={inputCls}
                            value={editForm.answerIndex}
                            onChange={(e) =>
                              setEditForm((f) =>
                                f ? { ...f, answerIndex: Number(e.target.value) } : f,
                              )
                            }
                            required
                          />
                        </label>

                        <label className="flex flex-col gap-1 text-sm">
                          {t('diagnosticItems.explanationLabel')}
                          <textarea
                            rows={2}
                            className="rounded-md border border-line bg-background px-3 py-2 text-base text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
                            value={editForm.explanation}
                            onChange={(e) =>
                              setEditForm((f) => f ? { ...f, explanation: e.target.value } : f)
                            }
                          />
                        </label>

                        <label className="flex flex-col gap-1 text-sm">
                          {t('diagnosticItems.tierLabel')}
                          <select
                            className={inputCls}
                            value={editForm.tier}
                            onChange={(e) =>
                              setEditForm((f) =>
                                f ? { ...f, tier: Number(e.target.value) as Tier } : f,
                              )
                            }
                          >
                            <option value={1}>{t('diagnosticItems.tier1')}</option>
                            <option value={2}>{t('diagnosticItems.tier2')}</option>
                            <option value={3}>{t('diagnosticItems.tier3')}</option>
                          </select>
                        </label>

                        {saveError && (
                          <p role="alert" className="text-sm text-danger-700">{saveError}</p>
                        )}

                        <div className="flex gap-3">
                          <button
                            type="submit"
                            disabled={patch.isPending}
                            className="min-h-[44px] rounded-md bg-brand-600 px-4 font-bold text-white hover:bg-brand-700 disabled:opacity-50"
                          >
                            {t('diagnosticItems.save')}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            className="min-h-[44px] rounded-md border border-line px-4 font-bold hover:bg-muted"
                          >
                            {t('diagnosticItems.cancel')}
                          </button>
                        </div>
                      </form>
                    </FormSection>
                  )}
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
