import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { childStatus, type ChildStatus } from '@/lib/format';
import { parentApi, type Child, type TierOverride } from '@/api/parent';
import { ApiError } from '@/api/client';
import { cn } from '@/lib/utils';
import { ChildAnalytics } from '@/components/ChildAnalytics';

const CHIP: Record<ChildStatus, string> = {
  active: 'bg-success-100 text-success-700',
  pending: 'bg-brand-100 text-brand-700',
  frozen: 'bg-slate-200 text-slate-700',
  declined: 'bg-danger-100 text-danger-700',
  deleted: 'bg-slate-300 text-slate-700 line-through',
};

export function ChildCard({ child }: { child: Child }) {
  const { t } = useTranslation('parent');
  const status = childStatus(child);
  const isDeleted = status === 'deleted';
  const qc = useQueryClient();
  const { toast } = useToast();
  const [confirmText, setConfirmText] = useState('');
  const [open, setOpen] = useState(false);

  const statusLabel = t(`childCard.status.${status}`);

  const freeze = useMutation({
    mutationFn: (frozen: boolean) => parentApi.freezeChild(child.user_id, frozen),
    onMutate: async (frozen) => {
      await qc.cancelQueries({ queryKey: ['children'] });
      const prev = qc.getQueryData<Child[]>(['children']);
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, is_active: !frozen } : c),
      );
      return { prev };
    },
    onError: (err, _frozen, ctx) => {
      qc.setQueryData(['children'], ctx?.prev);
      toast({
        title: t('childCard.toast.freezeErrorTitle'),
        description: err instanceof ApiError ? err.detail : undefined,
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['children'] }),
  });

  const pushToggle = useMutation({
    mutationFn: (enabled: boolean) => parentApi.setChildPush(child.user_id, enabled),
    onSuccess: (_d, enabled) => {
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, push_enabled: enabled } : c),
      );
    },
  });

  const biometricToggle = useMutation({
    mutationFn: (enabled: boolean) => parentApi.setChildBiometric(child.user_id, enabled),
    onSuccess: (_d, enabled) => {
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, biometric_allowed: enabled } : c),
      );
    },
  });

  const leaderboardConsentToggle = useMutation({
    mutationFn: (consent: boolean) => parentApi.setChildLeaderboardConsent(child.user_id, consent),
    onSuccess: (_d, consent) => {
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, leaderboard_consent: consent } : c),
      );
    },
  });

  const tier = useMutation({
    mutationFn: (value: TierOverride) => parentApi.setChildTier(child.user_id, value),
    onMutate: async (value) => {
      await qc.cancelQueries({ queryKey: ['children'] });
      const prev = qc.getQueryData<Child[]>(['children']);
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, tier_override: value } : c),
      );
      return { prev };
    },
    onError: (err, _value, ctx) => {
      qc.setQueryData(['children'], ctx?.prev);
      toast({
        title: t('childCard.toast.tierErrorTitle'),
        description: err instanceof ApiError ? err.detail : undefined,
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['children'] }),
  });

  const erase = useMutation({
    mutationFn: () => parentApi.eraseChild(child.user_id),
    onSuccess: () => {
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['children'] });
    },
    onError: (err) => {
      toast({
        title: t('childCard.toast.eraseErrorTitle'),
        description: err instanceof ApiError ? err.detail : undefined,
      });
    },
  });

  const currentTierLabel = child.age_tier === 'investor'
    ? t('childCard.experienceCurrentInvestor')
    : t('childCard.experienceCurrentExplorer');

  return (
    <article className="rounded-lg border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">{child.username}</h2>
          <p className="text-xs text-muted-foreground">{child.country_code}</p>
        </div>
        <span
          className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', CHIP[status])}
          aria-label={t('childCard.statusAriaLabel', { status: statusLabel })}
        >
          {statusLabel}
        </span>
      </div>

      {child.analytics && !isDeleted && (
        <ChildAnalytics analytics={child.analytics} />
      )}

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-3 sm:justify-between">
        <div className="flex items-center gap-2">
          <Switch
            id={`freeze-${child.user_id}`}
            checked={!child.is_active && !isDeleted}
            disabled={isDeleted || freeze.isPending}
            onCheckedChange={(frozen) => freeze.mutate(frozen)}
          />
          <Label htmlFor={`freeze-${child.user_id}`} className="text-sm">
            {t('childCard.freezeLabel')}
          </Label>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id={`push-${child.user_id}`}
            checked={child.push_enabled ?? false}
            disabled={isDeleted || pushToggle.isPending}
            onCheckedChange={(value) => pushToggle.mutate(value)}
          />
          <Label htmlFor={`push-${child.user_id}`} className="text-sm">
            {t('childCard.pushLabel')}
          </Label>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id={`biometric-${child.user_id}`}
            checked={child.biometric_allowed ?? false}
            disabled={isDeleted || biometricToggle.isPending}
            onCheckedChange={(value) => biometricToggle.mutate(value)}
          />
          <Label htmlFor={`biometric-${child.user_id}`} className="text-sm">
            {t('childCard.biometricLabel')}
          </Label>
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <Switch
              id={`leaderboard-consent-${child.user_id}`}
              checked={child.leaderboard_consent ?? false}
              disabled={isDeleted || leaderboardConsentToggle.isPending}
              onCheckedChange={(value) => leaderboardConsentToggle.mutate(value)}
              aria-describedby={`leaderboard-consent-help-${child.user_id}`}
            />
            <Label htmlFor={`leaderboard-consent-${child.user_id}`} className="text-sm">
              {t('childCard.leaderboardConsentLabel')}
            </Label>
          </div>
          <p id={`leaderboard-consent-help-${child.user_id}`} className="text-xs text-muted-foreground">
            {t('childCard.leaderboardConsentHelp')}
          </p>
        </div>

        <div className="flex items-center gap-2 text-sm">
          {child.is_premium
            ? <span className="font-semibold text-brand-700">{t('childCard.premium')}</span>
            : <span className="text-muted-foreground">{t('childCard.freePlan')}</span>}
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" disabled={isDeleted}>
              {t('childCard.deleteAccount')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('childCard.dialog.title', { username: child.username })}</DialogTitle>
              <DialogDescription>
                {t('childCard.dialog.description', { username: child.username })}
              </DialogDescription>
            </DialogHeader>
            <Input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              aria-label={t('childCard.dialog.confirmAriaLabel')}
            />
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>{t('childCard.dialog.cancel')}</Button>
              <Button
                variant="destructive"
                disabled={confirmText !== child.username || erase.isPending}
                onClick={() => erase.mutate()}
              >
                {erase.isPending ? t('childCard.dialog.deleting') : t('childCard.dialog.confirm')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Label htmlFor={`tier-${child.user_id}`} className="text-sm">
          {t('childCard.experienceMode')}
        </Label>
        <select
          id={`tier-${child.user_id}`}
          className="rounded-md border bg-background px-2 py-1 text-sm"
          value={child.tier_override ?? 'auto'}
          disabled={isDeleted || tier.isPending}
          onChange={(e) => {
            const v = e.target.value;
            tier.mutate(v === 'auto' ? null : (v as 'explorer' | 'investor'));
          }}
        >
          <option value="auto">{t('childCard.experienceAuto')}</option>
          <option value="explorer">{t('childCard.experienceExplorer')}</option>
          <option value="investor">{t('childCard.experienceInvestor')}</option>
        </select>
        <span className="text-xs text-muted-foreground">
          {t('childCard.experienceCurrent', { tier: currentTierLabel })}
        </span>
      </div>
    </article>
  );
}
