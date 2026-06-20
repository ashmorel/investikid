import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { marketApi, type MarketSummary } from '@/api/market';
import { ApiError } from '@/api/client';
import {
  useMarketBrief,
  useGenerateMarketBrief,
  useUpdateMarketBrief,
  useVerifyMarketBrief,
  useScaffoldMarket,
  useModules,
  useLevels,
  useGenerateModuleLessons,
  generateModuleLessons,
  useSuggestModules,
  useCreateModuleFromSuggestion,
  useGenerateNativeLessons,
  usePublishMarket,
  useUnpublishMarket,
  type AdminModule,
  type ModuleSuggestion,
} from '@/api/admin';
import CurriculumPanel from './CurriculumPanel';
import InlineDraftReview from './InlineDraftReview';

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Per-module result row for the market-wide runner. */
type RunnerResult =
  | { title: string; ok: true; generated: number; skipped: number }
  | { title: string; ok: false };

/** Admin market-content workflow (Sub-project E2).
 *  Pick a non-GB market → generate/edit/verify its brief → scaffold the
 *  module/level skeleton from GB → (per-level lessons via the existing draft
 *  review screens) → publish/unpublish. Controls are gated to mirror the
 *  backend: scaffold needs a verified brief; publish needs lessons. */
export default function MarketContent() {
  const { t } = useTranslation('admin');
  const marketsQ = useQuery({ queryKey: ['markets'], queryFn: () => marketApi.list() });
  const markets: MarketSummary[] = marketsQ.data ?? [];
  // Selected market: `picked` once the user chooses; otherwise default to the
  // first non-GB market in the loaded list (derived, no effect needed).
  const [picked, setPicked] = useState('');
  const defaultCode = (markets.find((m) => m.code !== 'GB') ?? markets[0])?.code ?? '';
  const code = picked || defaultCode;
  const setCode = setPicked;

  const selected = markets.find((m) => m.code === code);
  const briefQ = useMarketBrief(code);
  const generate = useGenerateMarketBrief(code);
  const update = useUpdateMarketBrief(code);
  const verify = useVerifyMarketBrief(code);
  const scaffold = useScaffoldMarket(code);
  const publish = usePublishMarket(code);
  const unpublish = useUnpublishMarket(code);

  const brief = briefQ.data;
  const isVerified = brief?.status === 'verified';
  const hasContent = !!selected?.has_content;

  // Modules for the lesson-generation step. The scaffold tags each new module
  // with `market_code=code` and preserves GB's `topic`/`order_index`, so we map
  // a market module to its GB source by matching (topic, order_index).
  const allModules = useModules().data ?? [];
  const marketModules = allModules
    .filter((m) => m.market_code === code)
    .sort((a, b) => a.order_index - b.order_index);

  // Editable JSON buffer, re-seeded from the loaded brief whenever the market
  // changes or a fresh brief arrives; preserves edits between unrelated renders.
  const [draftJson, setDraftJson] = useState('');
  const [jsonError, setJsonError] = useState('');
  const briefJson = brief?.brief_json;
  useEffect(() => {
    /* eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot seed
       of the editable JSON buffer from the fetched brief, keyed on (market,
       brief); mirrors the ref-guarded seeding pattern in AdminSettings. */
    if (briefJson) setDraftJson(JSON.stringify(briefJson, null, 2));
  }, [code, briefJson]);

  function handleSaveBrief() {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(draftJson);
    } catch {
      setJsonError(t('marketContent.brief.invalidJson'));
      return;
    }
    setJsonError('');
    update.mutate(parsed);
  }

  const publishError = (publish.error as { status?: number } | null)?.status;

  // ── Market-wide batch runner ──────────────────────────────────────
  // Run each module's per-module batch SEQUENTIALLY (await before the next) to
  // respect the 5/min rate limit. On 429 back off 13s and retry the same
  // module; on any other failure, record it and move on. Refresh module markers
  // (lesson counts) at the end.
  const qc = useQueryClient();
  const [includePopulated, setIncludePopulated] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ i: number; n: number } | null>(null);
  const [results, setResults] = useState<RunnerResult[]>([]);

  async function handleGenerateAll() {
    setRunning(true);
    setResults([]);
    const acc: RunnerResult[] = [];
    try {
      for (let i = 0; i < marketModules.length; i++) {
        setProgress({ i: i + 1, n: marketModules.length });
        const mod = marketModules[i];
        // Per-module inner loop: retry the SAME module on a 429 up to a cap, so a
        // persistently rate-limited module can't loop forever; then record it as
        // failed and the outer loop moves on.
        for (let attempt = 0; ; attempt++) {
          try {
            const res = await generateModuleLessons(mod.id, includePopulated);
            acc.push({
              title: mod.title,
              ok: true,
              generated: res.generated,
              skipped:
                res.skipped_populated + res.skipped_has_drafts + (res.skipped_no_source ?? 0) + (res.skipped_no_concepts ?? 0),
            });
            setResults([...acc]);
            break;
          } catch (e) {
            if (e instanceof ApiError && e.status === 429 && attempt < 3) {
              await sleep(13000);
              continue; // retry this module
            }
            acc.push({ title: mod.title, ok: false });
            setResults([...acc]);
            break;
          }
        }
      }
    } finally {
      setRunning(false);
      setProgress(null);
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    }
  }

  return (
    <div className="p-6 text-ink">
      <h1 className="mb-2 text-2xl font-bold text-ink">{t('marketContent.pageTitle')}</h1>
      <p className="mb-6 max-w-2xl text-sm text-muted-foreground">{t('marketContent.intro')}</p>

      {/* Market picker */}
      <div className="mb-6 max-w-xs">
        <label htmlFor="market-select" className="mb-1 block text-sm text-ink">
          {t('marketContent.marketLabel')}
        </label>
        <select
          id="market-select"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink"
        >
          {markets.map((m) => (
            <option key={m.code} value={m.code}>
              {m.name} ({m.code}){m.code === 'GB' ? ` — ${t('marketContent.sourceTag')}` : ''}
            </option>
          ))}
        </select>
      </div>

      {code === 'GB' && (
        <p className="mb-6 rounded-md border border-line bg-card px-4 py-3 text-sm text-muted-foreground">
          {t('marketContent.gbNote')}
        </p>
      )}

      {code && code !== 'GB' && (
        <div className="flex max-w-2xl flex-col gap-6">
          {/* Curriculum panel */}
          <CurriculumPanel marketCode={code} />

          {/* Step 1 — Brief */}
          <section aria-labelledby="brief-heading" className="rounded-md border border-line bg-card px-4 py-3">
            <h2 id="brief-heading" className="mb-1 text-lg font-semibold text-ink">
              {t('marketContent.brief.heading')}
            </h2>
            <p className="mb-3 text-sm text-muted-foreground">
              {t('marketContent.brief.status')}:{' '}
              <span className="font-medium text-ink">
                {brief ? t(`marketContent.brief.statusValue.${brief.status}`) : t('marketContent.brief.statusValue.none')}
              </span>
            </p>

            <div className="mb-3 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => generate.mutate()}
                disabled={generate.isPending}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {generate.isPending ? t('marketContent.brief.generating') : t('marketContent.brief.generate')}
              </button>
              <button
                type="button"
                onClick={() => verify.mutate()}
                disabled={verify.isPending || !brief || isVerified}
                className="rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {t('marketContent.brief.verify')}
              </button>
            </div>

            {generate.isError && (
              <p className="mb-2 text-sm text-danger-500" role="alert">{t('marketContent.brief.generateError')}</p>
            )}

            {brief && (
              <div>
                <label htmlFor="brief-json" className="mb-1 block text-sm text-ink">
                  {t('marketContent.brief.jsonLabel')}
                </label>
                <textarea
                  id="brief-json"
                  value={draftJson}
                  onChange={(e) => { setDraftJson(e.target.value); setJsonError(''); }}
                  rows={12}
                  spellCheck={false}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-ink"
                />
                {jsonError && <p className="mt-1 text-xs text-danger-500" role="alert">{jsonError}</p>}
                <button
                  type="button"
                  onClick={handleSaveBrief}
                  disabled={update.isPending}
                  className="mt-2 rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  {t('marketContent.brief.save')}
                </button>
                {update.isSuccess && (
                  <span className="ml-3 text-sm text-success-600" role="status">{t('marketContent.brief.saved')}</span>
                )}
              </div>
            )}
          </section>

          {/* Step 2 — Scaffold */}
          <section aria-labelledby="scaffold-heading" className="rounded-md border border-line bg-card px-4 py-3">
            <h2 id="scaffold-heading" className="mb-1 text-lg font-semibold text-ink">
              {t('marketContent.scaffold.heading')}
            </h2>
            <p className="mb-3 text-sm text-muted-foreground">{t('marketContent.scaffold.description')}</p>
            <button
              type="button"
              onClick={() => scaffold.mutate()}
              disabled={scaffold.isPending || !isVerified}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {scaffold.isPending ? t('marketContent.scaffold.running') : t('marketContent.scaffold.action')}
            </button>
            {!isVerified && (
              <p className="mt-2 text-xs text-muted-foreground">{t('marketContent.scaffold.needsVerified')}</p>
            )}
            {scaffold.isSuccess && scaffold.data && (
              <p className="mt-2 text-sm text-success-600" role="status">
                {scaffold.data.already_scaffolded
                  ? t('marketContent.scaffold.alreadyDone')
                  : t('marketContent.scaffold.result', {
                      modules: scaffold.data.modules_created,
                      levels: scaffold.data.levels_created,
                    })}
              </p>
            )}
          </section>

          {/* Intelligent suggestions — proactive modules this market needs */}
          {isVerified && (
            <section aria-labelledby="suggest-heading" className="rounded-md border border-line bg-card px-4 py-3">
              <h2 id="suggest-heading" className="mb-1 text-lg font-semibold text-ink">
                {t('marketContent.suggest.heading')}
              </h2>
              <p className="mb-3 text-sm text-muted-foreground">{t('marketContent.suggest.description')}</p>
              <ModuleSuggestions code={code} />
            </section>
          )}

          {/* Step 3 — Lessons (generate-market per level → existing draft-review flow) */}
          <section aria-labelledby="lessons-heading" className="rounded-md border border-line bg-card px-4 py-3">
            <h2 id="lessons-heading" className="mb-1 text-lg font-semibold text-ink">
              {t('marketContent.lessons.heading')}
            </h2>
            <p className="mb-3 text-sm text-muted-foreground">{t('marketContent.lessons.description')}</p>
            {marketModules.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('marketContent.lessons.notScaffolded')}</p>
            ) : (
              <div className="flex flex-col gap-4">
                {/* Market-wide batch runner */}
                <div className="flex flex-col gap-2 rounded-md border border-line bg-background px-3 py-2">
                  <label className="flex items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={includePopulated}
                      onChange={(e) => setIncludePopulated(e.target.checked)}
                      disabled={running}
                      className="h-4 w-4"
                    />
                    {t('marketContent.batch.includePopulated')}
                  </label>
                  <div>
                    <button
                      type="button"
                      onClick={handleGenerateAll}
                      disabled={running || !isVerified}
                      className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
                    >
                      {running ? t('marketContent.batch.running') : t('marketContent.batch.generateAllMarket')}
                    </button>
                  </div>
                  {progress && (
                    <p className="text-sm text-muted-foreground" role="status">
                      {t('marketContent.batch.progress', { i: progress.i, n: progress.n })}
                    </p>
                  )}
                  {!running && results.length > 0 && (
                    <ul className="flex flex-col gap-1" role="status">
                      {results.map((r, i) => (
                        <li key={`${r.title}-${i}`} className="text-xs text-ink">
                          <span className="font-medium">{r.title}</span>{': '}
                          {r.ok ? (
                            <span className="text-success-600">
                              {t('marketContent.batch.moduleResult', { generated: r.generated, skipped: r.skipped })}
                            </span>
                          ) : (
                            <span className="text-danger-500">{t('marketContent.batch.moduleFailed')}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {marketModules.map((mod) => (
                  <ModuleLessons
                    key={mod.id}
                    module={mod}
                    canGenerate={isVerified}
                    includePopulated={includePopulated}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Step 4 — Publish */}
          <section aria-labelledby="publish-heading" className="rounded-md border border-line bg-card px-4 py-3">
            <h2 id="publish-heading" className="mb-1 text-lg font-semibold text-ink">
              {t('marketContent.publish.heading')}
            </h2>
            <p className="mb-3 text-sm text-muted-foreground">
              {hasContent ? t('marketContent.publish.live') : t('marketContent.publish.notLive')}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => publish.mutate()}
                disabled={publish.isPending || hasContent}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {t('marketContent.publish.publish')}
              </button>
              <button
                type="button"
                onClick={() => unpublish.mutate()}
                disabled={unpublish.isPending || !hasContent}
                className="rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                {t('marketContent.publish.unpublish')}
              </button>
            </div>
            {publish.isError && (
              <p className="mt-2 text-sm text-danger-500" role="alert">
                {publishError === 409
                  ? t('marketContent.publish.noLessons')
                  : t('marketContent.publish.error')}
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

/** One scaffolded market module: lists its levels with batch generation controls. */
function ModuleLessons({
  module: mod,
  canGenerate,
  includePopulated,
}: {
  module: AdminModule;
  canGenerate: boolean;
  includePopulated: boolean;
}) {
  const { t } = useTranslation('admin');
  const levels = useLevels(mod.id).data ?? [];
  const sortedLevels = [...levels].sort((a, b) => a.order_index - b.order_index);
  const batch = useGenerateModuleLessons(mod.id);
  const [expandedLevelId, setExpandedLevelId] = useState<string | null>(null);

  return (
    <div className="rounded-md border border-line px-3 py-2">
      <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 className="text-sm font-semibold text-ink">{mod.title}</h3>
        <button
          type="button"
          onClick={() => batch.mutate(includePopulated)}
          disabled={!canGenerate || batch.isPending}
          className="rounded-md border border-line px-3 py-1 text-xs text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {batch.isPending ? t('marketContent.batch.running') : t('marketContent.batch.generateAllLevels')}
        </button>
        {batch.isError && (
          <span className="text-xs text-danger-500" role="alert">{t('marketContent.batch.moduleFailed')}</span>
        )}
        {batch.isSuccess && batch.data && (
          <span className="text-xs text-success-600" role="status">
            {t('marketContent.batch.moduleResult', {
              generated: batch.data.generated,
              skipped:
                batch.data.skipped_populated +
                batch.data.skipped_has_drafts +
                (batch.data.skipped_no_source ?? 0) +
                (batch.data.skipped_no_concepts ?? 0),
            })}
          </span>
        )}
      </div>
      {sortedLevels.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t('marketContent.lessons.noLevels')}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {sortedLevels.map((lvl) => (
            <LevelGenerator
              key={lvl.id}
              levelId={lvl.id}
              levelTitle={lvl.title}
              lessonCount={lvl.lesson_count}
              draftCount={lvl.draft_count}
              expanded={expandedLevelId === lvl.id}
              onToggleReview={() =>
                setExpandedLevelId((prev) => (prev === lvl.id ? null : lvl.id))
              }
            />
          ))}
        </ul>
      )}
    </div>
  );
}

/** A single level row with an inline "Review N draft(s)" toggle. */
function LevelGenerator({
  levelId,
  levelTitle,
  lessonCount,
  draftCount,
  expanded,
  onToggleReview,
}: {
  levelId: string;
  levelTitle: string;
  lessonCount: number;
  draftCount: number;
  expanded: boolean;
  onToggleReview: () => void;
}) {
  const { t } = useTranslation('admin');

  return (
    <li className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-sm text-ink">{levelTitle}</span>
        {lessonCount > 0 ? (
          <span className="rounded bg-success-100 px-2 py-0.5 text-xs text-success-700">
            {t('marketContent.lessons.published', { count: lessonCount })}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">{t('marketContent.lessons.noneYet')}</span>
        )}
        {draftCount > 0 && (
          <button
            type="button"
            onClick={onToggleReview}
            className="text-xs font-medium text-brand-600 underline hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {t('marketContent.lessons.reviewDrafts', { count: draftCount })}
          </button>
        )}
      </div>
      {expanded && (
        <InlineDraftReview levelId={levelId} onClose={onToggleReview} />
      )}
    </li>
  );
}

/** "Suggest modules" action: fetches model-proposed modules the market needs,
 *  then renders each as a SuggestionCard that owns its create + native-generate. */
function ModuleSuggestions({ code }: { code: string }) {
  const { t } = useTranslation('admin');
  const suggest = useSuggestModules(code);
  const suggestions = suggest.data;

  return (
    <div>
      <button
        type="button"
        onClick={() => suggest.mutate()}
        disabled={suggest.isPending}
        className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {suggest.isPending ? t('marketContent.suggest.loading') : t('marketContent.suggest.action')}
      </button>

      {suggest.isError && (
        <p className="mt-2 text-sm text-danger-500" role="alert">{t('marketContent.suggest.error')}</p>
      )}

      {suggest.isSuccess && suggestions && suggestions.length === 0 && (
        <p className="mt-2 text-sm text-muted-foreground" role="status">{t('marketContent.suggest.none')}</p>
      )}

      {suggestions && suggestions.length > 0 && (
        <ul className="mt-3 flex flex-col gap-3">
          {suggestions.map((s, i) => (
            <SuggestionCard key={`${s.title}-${i}`} code={code} suggestion={s} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** One suggestion: shows its metadata, a "Create this module" action, then —
 *  once created — a "Generate lessons" (native) trigger and a draft-review link.
 *  Hooks are called unconditionally; the native hook binds to the created level
 *  id once it exists (empty string disables it until then). */
function SuggestionCard({ code, suggestion }: { code: string; suggestion: ModuleSuggestion }) {
  const { t } = useTranslation('admin');
  const create = useCreateModuleFromSuggestion(code);
  const result = create.data;
  const generate = useGenerateNativeLessons(result?.level_id ?? '');

  return (
    <li className="rounded-md border border-line px-3 py-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-ink">{suggestion.title}</span>
        <span className="rounded bg-brand-100 px-2 py-0.5 text-xs text-brand-700">{suggestion.topic}</span>
        {suggestion.action === 'replace' ? (
          <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-900">
            {t('marketContent.suggest.actionReplace')}
            {suggestion.replaces ? ` — ${t('marketContent.suggest.replaces', { title: suggestion.replaces })}` : ''}
          </span>
        ) : (
          <span className="rounded bg-success-100 px-2 py-0.5 text-xs text-success-800">
            {t('marketContent.suggest.actionAdd')}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{suggestion.rationale}</p>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        {!result && (
          <button
            type="button"
            onClick={() => create.mutate(suggestion)}
            disabled={create.isPending}
            className="min-h-[44px] rounded-md border border-line px-3 py-1 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {create.isPending ? t('marketContent.suggest.creating') : t('marketContent.suggest.create')}
          </button>
        )}
        {create.isError && (
          <span className="text-xs text-danger-500" role="alert">{t('marketContent.suggest.createError')}</span>
        )}

        {result && (
          <>
            <span className="text-xs text-success-600" role="status">{t('marketContent.suggest.created')}</span>
            <button
              type="button"
              onClick={() => generate.mutate(result.suggested_concepts)}
              disabled={generate.isPending}
              className="min-h-[44px] rounded-md border border-line px-3 py-1 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {generate.isPending
                ? t('marketContent.suggest.generating')
                : t('marketContent.suggest.generate')}
            </button>
          </>
        )}
      </div>

      {result && generate.isError && (
        <p className="mt-1 text-xs text-danger-500" role="alert">{t('marketContent.lessons.error')}</p>
      )}
      {result && generate.isSuccess && generate.data && (
        <p className="mt-1 text-xs text-success-600" role="status">
          {t('marketContent.suggest.generated', {
            created: generate.data.created.length,
            skipped: generate.data.skipped,
          })}{' '}
          <Link
            to={`/admin/modules/${result.module_id}/levels/${result.level_id}/lessons`}
            className="underline hover:text-success-700"
          >
            {t('marketContent.suggest.reviewLink')}
          </Link>
        </p>
      )}
    </li>
  );
}
