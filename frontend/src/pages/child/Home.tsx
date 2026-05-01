import { useChildSession } from '@/hooks/useChildSession';

export default function Home() {
  const { data } = useChildSession();
  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold">Welcome, {data?.username}!</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Your account is set up. Lessons, the simulator, and stats are coming soon — keep an eye on
        the nav above.
      </p>
    </div>
  );
}
