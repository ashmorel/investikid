import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
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

const LABEL: Record<ChildStatus, string> = {
  active: 'Active', pending: 'Pending consent',
  frozen: 'Frozen', declined: 'Declined', deleted: 'Deleted',
};

export function ChildCard({ child }: { child: Child }) {
  const status = childStatus(child);
  const isDeleted = status === 'deleted';
  const qc = useQueryClient();
  const { toast } = useToast();
  const [confirmText, setConfirmText] = useState('');
  const [open, setOpen] = useState(false);

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
        title: 'Could not update child',
        description: err instanceof ApiError ? err.detail : 'Please try again.',
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['children'] }),
  });

  const premium = useMutation({
    mutationFn: (value: boolean) => parentApi.setChildPremium(child.user_id, value),
    onMutate: async (value) => {
      await qc.cancelQueries({ queryKey: ['children'] });
      const prev = qc.getQueryData<Child[]>(['children']);
      qc.setQueryData<Child[]>(['children'], (old) =>
        old?.map((c) => c.user_id === child.user_id ? { ...c, is_premium: value } : c),
      );
      return { prev };
    },
    onError: (err, _value, ctx) => {
      qc.setQueryData(['children'], ctx?.prev);
      toast({
        title: 'Could not update premium',
        description: err instanceof ApiError ? err.detail : 'Please try again.',
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['children'] }),
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
        title: 'Could not update experience mode',
        description: err instanceof ApiError ? err.detail : 'Please try again.',
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
        title: 'Could not delete account',
        description: err instanceof ApiError ? err.detail : 'Please try again.',
      });
    },
  });

  return (
    <article className="rounded-lg border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">{child.username}</h2>
          <p className="text-xs text-muted-foreground">{child.country_code}</p>
        </div>
        <span
          className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', CHIP[status])}
          aria-label={`Status: ${LABEL[status]}`}
        >
          {LABEL[status]}
        </span>
      </div>

      {child.analytics && !isDeleted && (
        <ChildAnalytics analytics={child.analytics} />
      )}

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Switch
            id={`freeze-${child.user_id}`}
            checked={!child.is_active && !isDeleted}
            disabled={isDeleted || freeze.isPending}
            onCheckedChange={(frozen) => freeze.mutate(frozen)}
          />
          <Label htmlFor={`freeze-${child.user_id}`} className="text-sm">
            Freeze account
          </Label>
        </div>

        <div className="flex items-center gap-2">
          <Switch
            id={`premium-${child.user_id}`}
            checked={child.is_premium}
            disabled={isDeleted || premium.isPending}
            onCheckedChange={(value) => premium.mutate(value)}
          />
          <Label htmlFor={`premium-${child.user_id}`} className="text-sm">
            {child.is_premium ? 'Premium ✨' : 'Premium'}
          </Label>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" disabled={isDeleted}>
              Delete account…
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete {child.username}?</DialogTitle>
              <DialogDescription>
                This soft-deletes the account. Your child will no longer be able to sign in.
                Type <span className="font-mono font-semibold">{child.username}</span> to confirm.
              </DialogDescription>
            </DialogHeader>
            <Input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              aria-label="Type child username to confirm"
            />
            <DialogFooter>
              <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
              <Button
                variant="destructive"
                disabled={confirmText !== child.username || erase.isPending}
                onClick={() => erase.mutate()}
              >
                {erase.isPending ? 'Deleting…' : 'Delete account'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Label htmlFor={`tier-${child.user_id}`} className="text-sm">
          Experience mode
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
          <option value="auto">Auto (recommended)</option>
          <option value="explorer">Explorer</option>
          <option value="investor">Investor</option>
        </select>
        <span className="text-xs text-muted-foreground">
          Currently: {child.age_tier === 'investor' ? 'Investor' : 'Explorer'}. Auto switches to Investor at 14.
        </span>
      </div>
    </article>
  );
}
