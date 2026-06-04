import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { REGIONS, type RegionCode } from '@/lib/region';

export function RegionSwitcher({ currentRegion }: { currentRegion: RegionCode }) {
  const qc = useQueryClient();

  const save = useMutation({
    mutationFn: (content_region: RegionCode) => authApi.updatePreferences({ content_region }),
    onSuccess: () => {
      // Lessons + recommendations re-filter (future-ready) and market re-features the exchange.
      for (const key of [
        ['me'], ['modules'], ['recommendations'], ['module-levels'], ['level-lessons'],
        ['market-featured'], ['market-search'], ['portfolio'], ['portfolio-history'],
      ]) {
        qc.invalidateQueries({ queryKey: key });
      }
    },
  });

  return (
    <div
      role="group"
      aria-label="Learning region"
      className="inline-flex rounded-xl border border-brand-100 bg-card p-1"
    >
      {REGIONS.map((r) => {
        const active = r.code === currentRegion;
        return (
          <button
            key={r.code}
            type="button"
            aria-current={active ? 'true' : undefined}
            disabled={save.isPending}
            onClick={() => { if (!active) save.mutate(r.code); }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-base font-semibold transition-colors min-h-[44px] ${
              active ? 'bg-brand-gradient text-white' : 'text-brand-700 hover:bg-brand-50'
            }`}
          >
            <span aria-hidden="true">{r.flag}</span>
            <span>{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
