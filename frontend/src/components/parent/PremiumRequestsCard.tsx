import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { premiumApi } from '@/api/premium';
import { Button } from '@/components/ui/button';
import { ParentZoneHeading } from '@/components/parent/ParentSection';

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
    // Brand palette (not accent/amber, which means "reward/streak" elsewhere)
    // so an action-needed item reads as action-needed.
    <section aria-label={t('premiumRequests.sectionAriaLabel')}>
      <ParentZoneHeading>{t('zones.needsApproval')}</ParentZoneHeading>
      <div className="rounded-2xl border border-brand-200 bg-brand-50 p-4">
        <ul className="space-y-3">
          {reqs.map((r) => (
            <li key={r.id} className="space-y-2">
              <p className="text-sm font-bold text-brand-900">
                {t('premiumRequests.requestDescription', { childUsername: r.child_username, contextLabel: r.context_label })}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  className="min-h-[44px] bg-brand-600 text-white hover:bg-brand-700"
                  onClick={() => onApprove?.()}
                  aria-label={t('premiumRequests.approveAriaLabel', { contextLabel: r.context_label, childUsername: r.child_username })}
                >
                  {t('premiumRequests.approve')}
                </Button>
                <Button
                  variant="outline"
                  className="min-h-[44px]"
                  onClick={() => decline.mutate(r.id)}
                  disabled={decline.isPending}
                  aria-label={t('premiumRequests.declineAriaLabel', { childUsername: r.child_username })}
                >
                  {t('premiumRequests.decline')}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
