import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { parentApi } from '@/api/parent';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';

const PREFERENCES_KEY = ['parent-preferences'];

export function NotificationPreferencesCard() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const q = useQuery({
    queryKey: PREFERENCES_KEY,
    queryFn: parentApi.getPreferences,
  });

  const mutation = useMutation({
    mutationFn: (optOut: boolean) => parentApi.updatePreferences(optOut),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PREFERENCES_KEY });
    },
    onError: () =>
      toast({
        title: "Couldn't update preferences",
        description: 'Please try again.',
        variant: 'destructive',
      }),
  });

  const optedIn = !(q.data?.trial_reminder_opt_out ?? false);

  return (
    <section className="mt-6 rounded-2xl border border-brand-100 bg-card p-4 text-gray-900">
      <h2 className="text-lg font-semibold">Email preferences</h2>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <label htmlFor="sub-email-toggle" className="block text-sm font-medium">
            Email me about my subscription
          </label>
          <p id="sub-email-help" className="mt-1 text-sm text-muted-foreground">
            Occasional reminders, like when a free trial is ending.
          </p>
        </div>
        <Switch
          id="sub-email-toggle"
          checked={optedIn}
          aria-describedby="sub-email-help"
          disabled={q.isLoading || mutation.isPending}
          onCheckedChange={(checked) => mutation.mutate(!checked)}
        />
      </div>
    </section>
  );
}
