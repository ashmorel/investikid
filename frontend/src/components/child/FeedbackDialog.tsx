import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Camera, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { BottomSheet } from '@/components/mobile/BottomSheet';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { useToast } from '@/hooks/use-toast';
import { captureScreen, fileToScreenshot, SCREENSHOT_MAX_CHARS } from '@/lib/screenshot';
import { useSubmitFeedback, type FeedbackType } from '@/api/feedback';

const MAX = 2000;
const MAX_FILE_BYTES = 12 * 1024 * 1024; // 12MB raw; compressed far smaller before send

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
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [capturing, setCapturing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setScreenshot(null);
  }

  function handleOpenChange(v: boolean) {
    if (!v) reset();
    onOpenChange(v);
  }

  // Capture the screen *behind* the dialog: briefly close it (without resetting
  // the draft — we call the parent setter directly, bypassing reset()), let it
  // animate out, snapshot, then reopen with the screenshot attached.
  async function handleCapture() {
    setError('');
    setCapturing(true);
    onOpenChange(false);
    await new Promise((r) => setTimeout(r, 350));
    try {
      setScreenshot(await captureScreen());
    } catch {
      setError(t('feedback.captureError'));
    } finally {
      onOpenChange(true);
      setCapturing(false);
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow re-selecting the same file
    if (!file) return;
    setError('');
    if (!file.type.startsWith('image/') || file.size > MAX_FILE_BYTES) {
      setError(t('feedback.uploadError'));
      return;
    }
    try {
      setScreenshot(await fileToScreenshot(file));
    } catch {
      setError(t('feedback.uploadError'));
    }
  }

  function handleSubmit() {
    setError('');
    // A screenshot over the backend cap would 422 the whole request and lose the
    // typed message too. Drop the image and send the text rather than failing.
    let outgoing = screenshot;
    if (outgoing && outgoing.length > SCREENSHOT_MAX_CHARS) {
      outgoing = null;
      toast({ title: t('feedback.screenshotTooLarge') });
    }
    submit.mutate(
      { feedback_type: type, message, page_url: window.location.pathname, screenshot: outgoing },
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

      {/* Optional screenshot */}
      <div className="space-y-2">
        <span className="text-sm font-medium">{t('feedback.screenshotLabel')}</span>
        {screenshot ? (
          <div className="relative inline-block">
            <img
              src={screenshot}
              alt={t('feedback.screenshotAlt')}
              className="max-h-32 rounded-lg border border-brand-200"
            />
            <button
              type="button"
              onClick={() => setScreenshot(null)}
              aria-label={t('feedback.removeScreenshot')}
              className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-ink text-white shadow"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" onClick={handleCapture} disabled={capturing}>
              <Camera className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {capturing ? t('feedback.capturing') : t('feedback.capture')}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={capturing}
            >
              <Upload className="mr-1.5 h-4 w-4" aria-hidden="true" />
              {t('feedback.upload')}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFile}
            />
          </div>
        )}
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
