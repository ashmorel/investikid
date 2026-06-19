import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { marketApi, type MarketSummary } from '@/api/market';
import {
  useMarketBrief,
  useGenerateMarketBrief,
  useUpdateMarketBrief,
  useVerifyMarketBrief,
  useScaffoldMarket,
  usePublishMarket,
  useUnpublishMarket,
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

          {/* Step 3 — Lessons (existing draft-review flow) */}
          <section aria-labelledby="lessons-heading" className="rounded-md border border-line bg-card px-4 py-3">
            <h2 id="lessons-heading" className="mb-1 text-lg font-semibold text-ink">
              {t('marketContent.lessons.heading')}
            </h2>
            <p className="text-sm text-muted-foreground">{t('marketContent.lessons.description')}</p>
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
