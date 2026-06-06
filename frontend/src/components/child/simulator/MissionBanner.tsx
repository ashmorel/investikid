import { type ActiveMission } from '@/api/missions';

export function MissionBanner({ mission }: { mission?: ActiveMission }) {
  if (!mission) return null;
  return (
    <section
      aria-label="Active mission"
      className="mb-4 flex items-start gap-3 rounded-2xl border-2 border-accent-400 bg-accent-50 p-4"
    >
      <span aria-hidden="true" className="text-2xl">🎯</span>
      <div>
        <p className="text-xs font-bold uppercase tracking-wider text-accent-700">Mission</p>
        <p className="text-base font-extrabold text-ink">{mission.title}</p>
        <p className="text-sm text-muted-foreground">{mission.prompt}</p>
      </div>
    </section>
  );
}
