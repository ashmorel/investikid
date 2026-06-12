import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { parentApi } from '@/api/parent';
import { ApiError } from '@/api/client';

export function DeleteAccountCard() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState('');
  const [error, setError] = useState<string | null>(null);

  const remove = useMutation({
    mutationFn: () => parentApi.deleteAccount(confirmEmail.trim()),
    onSuccess: () => {
      setOpen(false);
      qc.clear();
      navigate('/parent/login', { replace: true });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 400) {
        setError("That doesn't match your account email.");
      } else {
        setError('Something went wrong. Please try again.');
      }
    },
  });

  return (
    <section className="mt-6 rounded-2xl border border-danger-100 bg-card p-4 text-foreground">
      <h2 className="text-lg font-semibold text-danger-700">Danger zone</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Deleting your account permanently removes your account, all your children&apos;s accounts
        and their data, and cannot be undone.
      </p>
      <p className="mt-2 text-sm font-medium text-danger-700">
        If you have a paid subscription, deleting your account here does not cancel billing. Cancel
        it in the App Store (iOS), Google Play (Android), or via Manage Subscription first.
      </p>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) {
            setConfirmEmail('');
            setError(null);
          }
        }}
      >
        <DialogTrigger asChild>
          <Button variant="destructive" size="sm" className="mt-4">
            Delete my account…
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete my account?</DialogTitle>
            <DialogDescription>
              This permanently deletes your account and all your children&apos;s accounts and data.
              This cannot be undone. If you have a paid subscription, cancel it in the App Store,
              Google Play, or via Manage Subscription first — deleting here does not cancel billing.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="delete-confirm-email">Type your email to confirm</Label>
            <Input
              id="delete-confirm-email"
              type="email"
              autoComplete="off"
              value={confirmEmail}
              onChange={(e) => {
                setConfirmEmail(e.target.value);
                if (error) setError(null);
              }}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? 'delete-confirm-error' : undefined}
            />
            {error && (
              <p id="delete-confirm-error" className="text-sm text-danger-700">
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={confirmEmail.trim() === '' || remove.isPending}
              onClick={() => {
                setError(null);
                remove.mutate();
              }}
            >
              {remove.isPending ? 'Deleting…' : 'Delete account'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
