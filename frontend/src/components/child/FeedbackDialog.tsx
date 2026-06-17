import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useToast } from '@/hooks/use-toast';
import { useSubmitFeedback, type FeedbackType } from '@/api/feedback';

const MAX = 2000;

export function FeedbackDialog({
  open,
  onOpenChange,
  audience,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  audience: 'child' | 'parent';
}) {
  const { t } = useTranslation('child');
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const { toast } = useToast();
  const submit = useSubmitFeedback(audience);
  const [type, setType] = useState<FeedbackType>('bug');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const TYPE_OPTIONS: { value: FeedbackType; label: string }[] = [
    { value: 'bug', label: t('feedback.type.bug') },
    { value: 'feature', label: t('feedback.type.feature') },
    { value: 'general', label: t('feedback.type.general') },
  ];

  const PLACEHOLDER: Record<FeedbackType, string> = {
    bug: t('feedback.placeholder.bug'),
    feature: t('feedback.placeholder.feature'),
    general: t('feedback.placeholder.general'),
  };

  function reset() {
    setType('bug');
    setMessage('');
    setError('');
  }

  function handleOpenChange(v: boolean) {
    if (!v) reset();
    onOpenChange(v);
  }

  function handleSubmit() {
    setError('');
    submit.mutate(
      { feedback_type: type, message, page_url: window.location.pathname },
      {
        onSuccess: () => {
          toast({ title: t('feedback.success') });
          reset();
          onOpenChange(false);
        },
        onError: () => setError(t('feedback.error')),
      },
    );
  }

  const body = (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="feedback-type" className="text-sm font-medium">
          {t('feedback.typeLabel')}
        </label>
        <select
          id="feedback-type"
          className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
          value={type}
          onChange={(e) => setType(e.target.value as FeedbackType)}
        >
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      <div className="space-y-1.5">
        <label htmlFor="feedback-message" className="text-sm font-medium">
          {t('feedback.messageLabel')}
        </label>
        <textarea
          id="feedback-message"
          className="min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          placeholder={PLACEHOLDER[type]}
          value={message}
          maxLength={MAX}
          aria-describedby="feedback-counter"
          onChange={(e) => setMessage(e.target.value)}
        />
        <p id="feedback-counter" className="text-right text-xs text-muted-foreground">
          {message.length} / {MAX}
        </p>
      </div>
      <p role="alert" aria-live="assertive" className="min-h-[1.25rem] text-sm text-destructive">
        {error}
      </p>
      <Button
        type="button"
        disabled={submit.isPending || message.trim().length === 0}
        onClick={handleSubmit}
      >
        {submit.isPending ? t('feedback.sending') : t('feedback.submit')}
      </Button>
    </div>
  );

  return isMobile ? (
    <BottomSheet open={open} onOpenChange={handleOpenChange} title={t('feedback.title')}>
      {body}
    </BottomSheet>
  ) : (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('feedback.title')}</DialogTitle>
        </DialogHeader>
        {body}
      </DialogContent>
    </Dialog>
  );
}
