import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { parentApi, type ParentPreferences } from '@/api/parent';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';

const PREFERENCES_KEY = ['parent-preferences'];

export function NotificationPreferencesCard() {
  const { t } = useTranslation('parent');
  const qc = useQueryClient();
  const { toast } = useToast();

  const q = useQuery({
    queryKey: PREFERENCES_KEY,
    queryFn: parentApi.getPreferences,
  });

  const mutation = useMutation({
    mutationFn: (update: Partial<ParentPreferences>) => parentApi.updatePreferences(update),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PREFERENCES_KEY });
    },
    onError: () =>
      toast({
        title: t('notificationPreferences.toast.errorTitle'),
        description: t('notificationPreferences.toast.errorDesc'),
        variant: 'destructive',
      }),
  });

  const optedIn = !(q.data?.trial_reminder_opt_out ?? false);
  const digestOptedIn = !(q.data?.weekly_digest_opt_out ?? false);

  return (
    <section className="mt-6 rounded-2xl border border-brand-100 bg-card p-4 text-foreground">
      <h2 className="text-lg font-semibold">{t('notificationPreferences.heading')}</h2>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <label htmlFor="sub-email-toggle" className="block text-sm font-medium">
            {t('notificationPreferences.subEmailLabel')}
          </label>
          <p id="sub-email-help" className="mt-1 text-sm text-muted-foreground">
            {t('notificationPreferences.subEmailHelp')}
          </p>
        </div>
        <Switch
          id="sub-email-toggle"
          checked={optedIn}
          aria-describedby="sub-email-help"
          disabled={q.isLoading || mutation.isPending}
          onCheckedChange={(checked) => mutation.mutate({ trial_reminder_opt_out: !checked })}
        />
      </div>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <label htmlFor="digest-email-toggle" className="block text-sm font-medium">
            {t('notificationPreferences.digestLabel')}
          </label>
          <p id="digest-email-help" className="mt-1 text-sm text-muted-foreground">
            {t('notificationPreferences.digestHelp')}
          </p>
        </div>
        <Switch
          id="digest-email-toggle"
          checked={digestOptedIn}
          aria-describedby="digest-email-help"
          disabled={q.isLoading || mutation.isPending}
          onCheckedChange={(checked) => mutation.mutate({ weekly_digest_opt_out: !checked })}
        />
      </div>
    </section>
  );
}
