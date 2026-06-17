import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { parentApi } from '@/api/parent';
import { ApiError } from '@/api/client';

export function DeleteAccountCard() {
  const { t } = useTranslation('parent');
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
        setError(t('deleteAccount.error.emailMismatch'));
      } else {
        setError(t('deleteAccount.error.generic'));
      }
    },
  });

  return (
    <section className="mt-6 rounded-2xl border border-danger-100 bg-card p-4 text-foreground">
      <h2 className="text-lg font-semibold text-danger-700">{t('deleteAccount.heading')}</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {t('deleteAccount.body')}
      </p>
      <p className="mt-2 text-sm font-medium text-danger-700">
        {t('deleteAccount.billingWarning')}
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
            {t('deleteAccount.trigger')}
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('deleteAccount.dialog.title')}</DialogTitle>
            <DialogDescription>
              {t('deleteAccount.dialog.description')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="delete-confirm-email">{t('deleteAccount.dialog.confirmLabel')}</Label>
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
            <Button variant="ghost" onClick={() => setOpen(false)}>{t('deleteAccount.dialog.cancel')}</Button>
            <Button
              variant="destructive"
              disabled={confirmEmail.trim() === '' || remove.isPending}
              onClick={() => {
                setError(null);
                remove.mutate();
              }}
            >
              {remove.isPending ? t('deleteAccount.dialog.deleting') : t('deleteAccount.dialog.confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
