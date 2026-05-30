import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useToast } from '@/hooks/use-toast';
import { useSubmitFeedback, type FeedbackType } from '@/api/feedback';

const TYPE_OPTIONS: { value: FeedbackType; label: string }[] = [
  { value: 'bug', label: 'Bug Report' },
  { value: 'feature', label: 'Feature Request' },
  { value: 'general', label: 'General Feedback' },
];

const PLACEHOLDER: Record<FeedbackType, string> = {
  bug: 'Describe the bug you encountered…',
  feature: 'What feature would you like to see?',
  general: 'Share your thoughts…',
};

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
  const isMobile = !useMediaQuery('(min-width: 768px)');
  const { toast } = useToast();
  const submit = useSubmitFeedback(audience);
  const [type, setType] = useState<FeedbackType>('bug');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

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
          toast({ title: 'Thanks for your feedback!' });
          reset();
          onOpenChange(false);
        },
        onError: () => setError('Could not send feedback. Please try again.'),
      },
    );
  }

  const body = (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="feedback-type" className="text-sm font-medium">
          Type
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
          Message
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
        {submit.isPending ? 'Sending…' : 'Send Feedback'}
      </Button>
    </div>
  );

  return isMobile ? (
    <BottomSheet open={open} onOpenChange={handleOpenChange} title="Send feedback">
      {body}
    </BottomSheet>
  ) : (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send feedback</DialogTitle>
        </DialogHeader>
        {body}
      </DialogContent>
    </Dialog>
  );
}
