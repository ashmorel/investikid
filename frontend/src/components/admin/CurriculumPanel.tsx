import { useTranslation } from 'react-i18next';
import {
  useCurriculum,
  useDesignCurriculum,
  useAcceptCurriculum,
  type CurriculumLevelNode,
  type CurriculumModuleNode,
} from '@/api/admin';

const TIER_KEYS: Record<number, string> = { 1: 'tier1', 2: 'tier2', 3: 'tier3' };

function TierBadge({ tier }: { tier: number }) {
  const { t } = useTranslation('admin');
  const key = TIER_KEYS[tier] ?? 'tier1';
  return (
    <span className="rounded bg-brand-100 px-2 py-0.5 text-xs text-brand-700">
      {t(`marketContent.curriculum.${key}`)}
    </span>
  );
}

function LevelRow({ level }: { level: CurriculumLevelNode }) {
  return (
    <li className="flex flex-wrap items-center gap-2 py-0.5 text-sm text-ink">
      <TierBadge tier={level.complexity_tier} />
      <span>{level.title}</span>
    </li>
  );
}

function ModuleCard({ module: mod }: { module: CurriculumModuleNode }) {
  return (
    <div className="rounded-md border border-line bg-background px-3 py-2">
      <div className="mb-1 flex items-center gap-2">
        <span aria-hidden="true">{mod.icon}</span>
        <span className="font-semibold text-ink">{mod.title}</span>
      </div>
      {mod.levels.length > 0 && (
        <ul>
          {mod.levels
            .slice()
            .sort((a, b) => a.order_index - b.order_index)
            .map((lvl, i) => (
              <LevelRow key={lvl.level_id ?? `${lvl.title}-${i}`} level={lvl} />
            ))}
        </ul>
      )}
    </div>
  );
}

export default function CurriculumPanel({ marketCode }: { marketCode: string }) {
  const { t } = useTranslation('admin');
  const { data, isLoading } = useCurriculum(marketCode);
  const design = useDesignCurriculum(marketCode);
  const accept = useAcceptCurriculum(marketCode);

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        {t('layout.loading')}
      </p>
    );
  }

  if (data === null || data === undefined) {
    return (
      <section
        aria-labelledby="curriculum-heading"
        className="rounded-md border border-line bg-card px-4 py-3"
      >
        <h2 id="curriculum-heading" className="mb-3 text-lg font-semibold text-ink">
          {t('marketContent.curriculum.heading', 'Curriculum')}
        </h2>
        <p className="mb-3 text-sm text-muted-foreground">
          {t('marketContent.curriculum.noCurriculum')}
        </p>
        <button
          type="button"
          onClick={() => design.mutate()}
          disabled={design.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {design.isPending
            ? t('marketContent.curriculum.designing')
            : t('marketContent.curriculum.design')}
        </button>
      </section>
    );
  }

  const { proposal, coverage } = data;
  const sortedModules = proposal.modules
    .slice()
    .sort((a, b) => a.order_index - b.order_index);

  return (
    <section
      aria-labelledby="curriculum-heading"
      className="rounded-md border border-line bg-card px-4 py-3"
    >
      <h2 id="curriculum-heading" className="mb-3 text-lg font-semibold text-ink">
        {t('marketContent.curriculum.heading', 'Curriculum')}
      </h2>

      {/* Module/level tree */}
      <div className="mb-4 flex flex-col gap-2">
        {sortedModules.map((mod, i) => (
          <ModuleCard key={`${mod.topic}-${i}`} module={mod} />
        ))}
      </div>

      {/* Coverage */}
      <div className="mb-4" role="status">
        {coverage.ok ? (
          <p className="flex items-center gap-1 text-sm text-success-600">
            {/* eslint-disable-next-line i18next/no-literal-string -- decorative glyph, aria-hidden */}
            <span aria-hidden="true">✓</span>
            {t('marketContent.curriculum.coverageOk')}
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {coverage.missing_backbone.map((key) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-900"
              >
                <span aria-hidden="true">⚠</span>
                {t('marketContent.curriculum.coverageGap', { key })}
              </span>
            ))}
            {coverage.regressions.map((key) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-900"
              >
                <span aria-hidden="true">⚠</span>
                {t('marketContent.curriculum.coverageRegression', { key })}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => accept.mutate()}
          disabled={accept.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {accept.isPending
            ? t('marketContent.curriculum.accepting')
            : t('marketContent.curriculum.accept')}
        </button>
        <button
          type="button"
          onClick={() => design.mutate()}
          disabled={design.isPending}
          className="rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {design.isPending
            ? t('marketContent.curriculum.designing')
            : t('marketContent.curriculum.regenerate')}
        </button>
      </div>

      {accept.isSuccess && (
        <p className="mt-2 text-sm text-success-600" role="status">
          {t('marketContent.curriculum.accepted')}
        </p>
      )}
    </section>
  );
}
