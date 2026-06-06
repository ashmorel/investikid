import { useQuery } from '@tanstack/react-query';
import { premiumApi } from '@/api/premium';

export function PremiumRequestsCard() {
  const q = useQuery({ queryKey: ['premium-requests'], queryFn: premiumApi.parentRequests, retry: false });
  const reqs = q.data ?? [];
  if (!reqs.length) return null;
  return (
    <section aria-label="Premium requests" className="mb-4 rounded-2xl border border-accent-200 bg-accent-50 p-4">
      <p className="text-sm font-bold text-accent-700">✨ Premium requested</p>
      <ul className="mt-1 space-y-0.5">
        {reqs.map((r) => (
          <li key={r.id} className="text-sm text-ink">
            <strong>{r.child_username}</strong> asked to unlock <em>{r.context_label}</em>
          </li>
        ))}
      </ul>
    </section>
  );
}
