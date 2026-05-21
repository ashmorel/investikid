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
import { parentApi, type Child } from '@/api/parent';
import { ApiError } from '@/api/client';
import { cn } from '@/lib/utils';

const CHIP: Record<ChildStatus, string> = {
  active: 'bg-emerald-100 text-emerald-900',
  pending: 'bg-amber-100 text-amber-900',
  frozen: 'bg-slate-200 text-slate-700',
  declined: 'bg-rose-100 text-rose-900',
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

        {child.is_premium && (
          <span className="text-xs font-medium text-amber-600">Premium ✨</span>
        )}

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
    </article>
  );
}
