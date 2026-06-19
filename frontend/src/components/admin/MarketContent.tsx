import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { marketApi, type MarketSummary } from '@/api/market';
import {
  useMarketBrief,
  useGenerateMarketBrief,
  useUpdateMarketBrief,
  useVerifyMarketBrief,
  useScaffoldMarket,
  useModules,
  useLevels,
  useGenerateMarketLessons,
  useSuggestModules,
  useCreateModuleFromSuggestion,
  useGenerateNativeLessons,
  usePublishMarket,
  useUnpublishMarket,
  type AdminModule,
  type ModuleSuggestion,
} from '@/api/admin';

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
  const gbModules = allModules.filter((m) => m.market_code === 'GB');

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
                {marketModules.map((mod) => {
                  const gbModule = matchGbModule(gbModules, mod);
                  return (
                    <ModuleLessons
                      key={mod.id}
                      module={mod}
                      gbModule={gbModule}
                      canGenerate={isVerified}
                    />
                  );
                })}
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

/** Match a market module to its GB source by the fields the scaffold preserves
 *  (topic + order_index). Returns the GB module or undefined if no robust
 *  single match exists (so the caller can disable generation, not guess). */
function matchGbModule(gbModules: AdminModule[], marketModule: AdminModule): AdminModule | undefined {
  const matches = gbModules.filter(
    (g) => g.topic === marketModule.topic && g.order_index === marketModule.order_index,
  );
  return matches.length === 1 ? matches[0] : undefined;
}

/** One scaffolded market module: lists its levels, each with a generate-market
 *  trigger wired to the matched GB source level. */
function ModuleLessons({
  module: mod,
  gbModule,
  canGenerate,
}: {
  module: AdminModule;
  gbModule: AdminModule | undefined;
  canGenerate: boolean;
}) {
  const { t } = useTranslation('admin');
  const levels = useLevels(mod.id).data ?? [];
  const gbLevels = useLevels(gbModule?.id ?? '').data ?? [];
  const sortedLevels = [...levels].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="rounded-md border border-line px-3 py-2">
      <h3 className="mb-2 text-sm font-semibold text-ink">{mod.title}</h3>
      {sortedLevels.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t('marketContent.lessons.noLevels')}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {sortedLevels.map((lvl) => {
            // Within a module, market level[j] ↔ GB level[j] by order_index.
            const gbMatches = gbModule
              ? gbLevels.filter((g) => g.order_index === lvl.order_index)
              : [];
            const sourceLevel = gbMatches.length === 1 ? gbMatches[0] : undefined;
            return (
              <LevelGenerator
                key={lvl.id}
                moduleId={mod.id}
                levelId={lvl.id}
                levelTitle={lvl.title}
                sourceLevelId={sourceLevel?.id}
                canGenerate={canGenerate}
              />
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** A single level row with its "Generate lessons (from GB)" trigger. Disabled
 *  unless the brief is verified and a unique GB source level matched. */
function LevelGenerator({
  moduleId,
  levelId,
  levelTitle,
  sourceLevelId,
  canGenerate,
}: {
  moduleId: string;
  levelId: string;
  levelTitle: string;
  sourceLevelId: string | undefined;
  canGenerate: boolean;
}) {
  const { t } = useTranslation('admin');
  const generate = useGenerateMarketLessons(levelId);
  const enabled = canGenerate && !!sourceLevelId && !generate.isPending;

  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="text-sm text-ink">{levelTitle}</span>
      <button
        type="button"
        onClick={() => sourceLevelId && generate.mutate(sourceLevelId)}
        disabled={!enabled}
        className="rounded-md border border-line px-3 py-1 text-xs text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {generate.isPending
          ? t('marketContent.lessons.generating')
          : t('marketContent.lessons.generate')}
      </button>
      {!sourceLevelId && (
        <span className="text-xs text-muted-foreground">{t('marketContent.lessons.noSource')}</span>
      )}
      {generate.isError && (
        <span className="text-xs text-danger-500" role="alert">{t('marketContent.lessons.error')}</span>
      )}
      {generate.isSuccess && generate.data && (
        <span className="text-xs text-success-600" role="status">
          {t('marketContent.lessons.result', {
            created: generate.data.created.length,
            skipped: generate.data.skipped,
          })}{' '}
          <Link
            to={`/admin/modules/${moduleId}/levels/${levelId}/lessons`}
            className="underline hover:text-success-700"
          >
            {t('marketContent.lessons.reviewLink')}
          </Link>
        </span>
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
