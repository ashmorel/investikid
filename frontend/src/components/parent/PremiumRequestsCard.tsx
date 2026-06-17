import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { premiumApi } from '@/api/premium';
import { Button } from '@/components/ui/button';

const REQUESTS_KEY = ['premium-requests'];

export function PremiumRequestsCard({ onApprove }: { onApprove?: () => void }) {
  const { t } = useTranslation('parent');
  const qc = useQueryClient();
  const q = useQuery({ queryKey: REQUESTS_KEY, queryFn: premiumApi.parentRequests, retry: false });
  const decline = useMutation({
    mutationFn: (id: string) => premiumApi.declineRequest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: REQUESTS_KEY }),
  });
  const reqs = q.data ?? [];
  if (!reqs.length) return null;
  return (
    <section aria-label={t('premiumRequests.sectionAriaLabel')} className="mb-4 rounded-2xl border border-accent-200 bg-accent-50 p-4">
      <p className="text-sm font-bold text-accent-700">{t('premiumRequests.requested')}</p>
      <ul className="mt-2 space-y-2">
        {reqs.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 text-sm text-ink">
            <span>
              <strong>{r.child_username}</strong> asked to unlock <em>{r.context_label}</em>
            </span>
            <span className="flex shrink-0 gap-2">
              <Button
                size="sm"
                onClick={() => onApprove?.()}
                aria-label={t('premiumRequests.approveAriaLabel', { contextLabel: r.context_label, childUsername: r.child_username })}
              >
                {t('premiumRequests.approve')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => decline.mutate(r.id)}
                disabled={decline.isPending}
                aria-label={t('premiumRequests.declineAriaLabel', { childUsername: r.child_username })}
              >
                {t('premiumRequests.decline')}
              </Button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
