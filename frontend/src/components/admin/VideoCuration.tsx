import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useModules, useLevels } from '@/api/admin';
import { marketApi } from '@/api/market';
import {
  listVideoCandidates,
  approveVideoCandidate,
  skipVideoCandidate,
  type VideoCandidate,
} from '@/api/videoCuration';

// ── Per-row component so each row can call useLevels with its own state ──
interface CandidateRowProps {
  candidate: VideoCandidate;
  modules: { id: string; title: string; market_code?: string }[];
  onApprove: (id: string, moduleId: string, levelId: string) => void;
  onSkip: (id: string) => void;
  approving: boolean;
  skipping: boolean;
}

function CandidateRow({
  candidate,
  modules,
  onApprove,
  onSkip,
  approving,
  skipping,
}: CandidateRowProps) {
  const { t } = useTranslation('admin');

  const marketModules = modules.filter(
    (m) => !m.market_code || m.market_code === candidate.market_code,
  );

  const [selectedModuleId, setSelectedModuleId] = useState<string>(
    candidate.suggested_module_id ?? '',
  );
  const [selectedLevelId, setSelectedLevelId] = useState<string>(
    candidate.suggested_level_id ?? '',
  );

  const levelsQ = useLevels(selectedModuleId);
  const levels = levelsQ.data ?? [];

  function handleModuleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedModuleId(e.target.value);
    setSelectedLevelId('');
  }

  const canApprove =
    candidate.embeddable === true &&
    selectedModuleId !== '' &&
    selectedLevelId !== '' &&
    !approving;

  return (
    <li className="rounded-xl border border-line bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <iframe
          title={candidate.title}
          src={`https://www.youtube.com/embed/${candidate.youtube_id}`}
          className="aspect-video w-full sm:w-80"
          allow="encrypted-media"
        />
        <div className="flex-1 space-y-3">
          <div className="font-semibold text-ink">{candidate.title}</div>
          <div className="text-xs text-muted-foreground">
            {candidate.source} · {candidate.market_code}
            {candidate.origin_context ? ` · ${candidate.origin_context}` : ''}
          </div>

          {candidate.embeddable === false && (
            <p className="text-xs font-semibold text-red-600">
              {t('videoCuration.blocked', { reason: candidate.health_detail ?? '' })}
            </p>
          )}

          {/* Module select */}
          <div className="space-y-1">
            <label
              htmlFor={`module-${candidate.id}`}
              className="block text-xs font-medium text-ink"
            >
              {t('videoCuration.moduleLabel')}
            </label>
            <select
              id={`module-${candidate.id}`}
              aria-label={t('videoCuration.moduleLabel')}
              value={selectedModuleId}
              onChange={handleModuleChange}
              className="min-h-[44px] w-full rounded-md border border-line bg-background px-3 py-2 text-sm text-ink"
            >
              <option value="">{t('videoCuration.selectModule')}</option>
              {marketModules.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.title}
                </option>
              ))}
            </select>
          </div>

          {/* Level select */}
          <div className="space-y-1">
            <label
              htmlFor={`level-${candidate.id}`}
              className="block text-xs font-medium text-ink"
            >
              {t('videoCuration.levelLabel')}
            </label>
            <select
              id={`level-${candidate.id}`}
              aria-label={t('videoCuration.levelLabel')}
              value={selectedLevelId}
              onChange={(e) => setSelectedLevelId(e.target.value)}
              disabled={!selectedModuleId || levelsQ.isLoading}
              className="min-h-[44px] w-full rounded-md border border-line bg-background px-3 py-2 text-sm text-ink disabled:opacity-50"
            >
              <option value="">{t('videoCuration.selectLevel')}</option>
              {levels.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.title}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              disabled={!canApprove}
              onClick={() => onApprove(candidate.id, selectedModuleId, selectedLevelId)}
              className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {t('videoCuration.approve')}
            </button>
            <button
              type="button"
              disabled={skipping}
              onClick={() => onSkip(candidate.id)}
              className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink"
            >
              {t('videoCuration.skip')}
            </button>
          </div>
        </div>
      </div>
    </li>
  );
}

// ── Page component ───────────────────────────────────────────────────────────
export default function VideoCuration() {
  const { t } = useTranslation('admin');
  const qc = useQueryClient();
  const [market, setMarket] = useState<string>('');

  const marketsQ = useQuery({
    queryKey: ['markets', 'list'],
    queryFn: () => marketApi.list(),
  });

  const candidatesQ = useQuery({
    queryKey: ['admin', 'video-candidates', market],
    queryFn: () => listVideoCandidates(market || undefined),
  });

  const modulesQ = useModules();
  const modules = modulesQ.data ?? [];

  const approveMutation = useMutation({
    mutationFn: (v: { id: string; module_id: string; level_id: string }) =>
      approveVideoCandidate(v.id, { module_id: v.module_id, level_id: v.level_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'video-candidates'] }),
  });

  const skipMutation = useMutation({
    mutationFn: (id: string) => skipVideoCandidate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'video-candidates'] }),
  });

  const candidates = candidatesQ.data ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-extrabold text-ink">{t('videoCuration.heading')}</h1>
      <p className="text-sm text-muted-foreground">{t('videoCuration.subtitle')}</p>

      {/* Market filter */}
      <div>
        <label htmlFor="vc-market-filter" className="sr-only">
          {t('videoCuration.marketFilterLabel')}
        </label>
        <select
          id="vc-market-filter"
          aria-label={t('videoCuration.marketFilterLabel')}
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          className="min-h-[44px] rounded-md border border-line bg-background px-3 py-2 text-sm text-ink"
        >
          <option value="">{t('videoCuration.allMarkets')}</option>
          {(marketsQ.data ?? []).map((m) => (
            <option key={m.code} value={m.code}>
              {m.name}
            </option>
          ))}
        </select>
      </div>

      {candidatesQ.isLoading && (
        <p className="text-sm text-muted-foreground">{t('videoCuration.loading')}</p>
      )}

      {candidates.length === 0 && !candidatesQ.isLoading && (
        <p className="text-sm text-muted-foreground">{t('videoCuration.empty')}</p>
      )}

      <ul className="space-y-4">
        {candidates.map((c) => (
          <CandidateRow
            key={c.id}
            candidate={c}
            modules={modules}
            onApprove={(id, moduleId, levelId) =>
              approveMutation.mutate({ id, module_id: moduleId, level_id: levelId })
            }
            onSkip={(id) => skipMutation.mutate(id)}
            approving={approveMutation.isPending}
            skipping={skipMutation.isPending}
          />
        ))}
      </ul>
    </div>
  );
}
