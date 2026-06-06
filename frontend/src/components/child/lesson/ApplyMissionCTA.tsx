import { Link } from 'react-router-dom';
import { type ActiveMission } from '@/api/missions';

export function ApplyMissionCTA({ mission }: { mission: ActiveMission }) {
  return (
    <section
      aria-label="Apply what you learned"
      className="mt-4 rounded-2xl border-2 border-brand-200 bg-brand-50 p-5 text-center"
    >
      <p className="text-sm font-bold uppercase tracking-wider text-brand-700">Your mission</p>
      <p className="mt-1 text-lg font-extrabold text-ink">{mission.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{mission.prompt}</p>
      <Link
        to={`/simulator?mission=${mission.id}`}
        className="mt-3 inline-block rounded-full bg-brand-gradient px-5 py-2.5 text-sm font-bold text-white shadow"
      >
        Try it in the simulator
      </Link>
    </section>
  );
}
