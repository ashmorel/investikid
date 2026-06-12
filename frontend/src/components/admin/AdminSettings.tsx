import { useEffect, useRef, useState } from 'react';
import { useAdminSettings, useUpdateAdminSettings } from '@/api/admin';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function AdminSettings() {
  const { data, isLoading, isError: isLoadError } = useAdminSettings();
  const update = useUpdateAdminSettings();

  const [emails, setEmails] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState('');
  const [eventTitle, setEventTitle] = useState('');
  const [eventEmoji, setEventEmoji] = useState('');
  const [eventStart, setEventStart] = useState('');
  const [eventEnd, setEventEnd] = useState('');
  const [eventBonus, setEventBonus] = useState(0);
  // Seed local state once data arrives; seeded ref avoids re-seeding on invalidate/refetch
  const seeded = useRef(false);

  useEffect(() => {
    if (data && !seeded.current) {
      setEmails(data.alert_emails);
      if (data.seasonal_event) {
        setEventTitle(data.seasonal_event.title);
        setEventEmoji(data.seasonal_event.emoji);
        setEventStart(data.seasonal_event.starts_at.slice(0, 10));
        setEventEnd(data.seasonal_event.ends_at.slice(0, 10));
        setEventBonus(data.seasonal_event.xp_bonus_pct);
      }
      seeded.current = true;
    }
  }, [data]);

  function handleAdd() {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      setInputError('Enter an email address.');
      return;
    }
    if (!EMAIL_RE.test(trimmed)) {
      setInputError('Not a valid email address.');
      return;
    }
    if (emails.includes(trimmed)) {
      setInputError('Already in the list.');
      return;
    }
    setEmails((prev) => [...prev, trimmed]);
    setInputValue('');
    setInputError('');
    // Reset mutation status so previous success/error banner is cleared
    update.reset();
  }

  function handleRemove(email: string) {
    setEmails((prev) => prev.filter((e) => e !== email));
    update.reset();
  }

  function handleSave() {
    update.mutate({
      alert_emails: emails,
      ...(eventTitle && eventStart && eventEnd
        ? {
            seasonal_event: {
              title: eventTitle,
              emoji: eventEmoji,
              starts_at: new Date(eventStart).toISOString(),
              ends_at: new Date(`${eventEnd}T23:59:59Z`).toISOString(),
              xp_bonus_pct: eventBonus,
            },
          }
        : {}),
    });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  }

  if (isLoading) {
    return <p className="p-6 text-muted-foreground">Loading settings…</p>;
  }

  if (isLoadError) {
    return <p className="p-6 text-danger-500">Failed to load settings. Refresh to try again.</p>;
  }

  return (
    <div className="p-6 text-ink">
      <h1 className="mb-6 text-2xl font-bold text-ink">Settings</h1>

      <section aria-labelledby="alert-emails-heading" className="max-w-xl">
        <h2 id="alert-emails-heading" className="mb-1 text-lg font-semibold text-ink">
          Alert emails
        </h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Who gets notified when the AI helper is degraded or down.
        </p>

        {/* Add email row */}
        <div className="mb-4 flex gap-2">
          <div className="flex-1">
            <label htmlFor="new-alert-email" className="mb-1 block text-sm text-muted-foreground">
              Add email address
            </label>
            <input
              id="new-alert-email"
              type="email"
              value={inputValue}
              onChange={(e) => { setInputValue(e.target.value); setInputError(''); }}
              onKeyDown={handleKeyDown}
              placeholder="admin@example.com"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-brand-500"
              aria-describedby={inputError ? 'email-input-error' : undefined}
            />
            {inputError && (
              <p id="email-input-error" className="mt-1 text-xs text-danger-500" role="alert">
                {inputError}
              </p>
            )}
          </div>
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleAdd}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              Add
            </button>
          </div>
        </div>

        {/* Email list */}
        {emails.length === 0 ? (
          <p className="mb-4 rounded-md border border-line bg-card px-4 py-3 text-sm text-muted-foreground">
            No alert recipients — alerts are currently off.
          </p>
        ) : (
          <ul aria-label="Alert email recipients" className="mb-4 flex flex-col gap-2">
            {emails.map((email) => (
              <li
                key={email}
                className="flex items-center justify-between rounded-md border border-line bg-card px-3 py-2"
              >
                <span className="text-sm text-ink">{email}</span>
                <button
                  type="button"
                  onClick={() => handleRemove(email)}
                  aria-label={`Remove ${email}`}
                  className="ml-3 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-brand-50 hover:text-danger-500 focus:outline-none focus:ring-1 focus:ring-danger-500"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Seasonal event (M9) — deploy-free, lives in AppSetting */}
        <fieldset className="mb-4 rounded-md border border-line bg-card px-4 py-3">
          <legend className="px-1 text-sm font-semibold text-ink">Seasonal event</legend>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label htmlFor="ev-title" className="mb-1 block text-sm text-ink">Title</label>
              <input id="ev-title" value={eventTitle} maxLength={60} onChange={(e) => setEventTitle(e.target.value)}
                placeholder="Spooky Savings Week"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-emoji" className="mb-1 block text-sm text-ink">Emoji</label>
              <input id="ev-emoji" value={eventEmoji} maxLength={8} onChange={(e) => setEventEmoji(e.target.value)}
                placeholder="🎃" className="w-24 rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-bonus" className="mb-1 block text-sm text-ink">Bonus XP %</label>
              <input id="ev-bonus" type="number" min={0} max={100} value={eventBonus}
                onChange={(e) => setEventBonus(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-start" className="mb-1 block text-sm text-ink">Starts</label>
              <input id="ev-start" type="date" value={eventStart} onChange={(e) => setEventStart(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-end" className="mb-1 block text-sm text-ink">Ends</label>
              <input id="ev-end" type="date" value={eventEnd} onChange={(e) => setEventEnd(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Children see a banner on Home and lesson XP gets the bonus while the event is live. Save applies it; Clear removes it.
          </p>
          <button
            type="button"
            onClick={() => {
              setEventTitle(''); setEventEmoji(''); setEventStart(''); setEventEnd(''); setEventBonus(0);
              update.mutate({ alert_emails: emails, clear_seasonal_event: true });
            }}
            className="mt-2 rounded-md border border-line px-3 py-1.5 text-xs text-muted-foreground hover:bg-brand-50"
          >
            Clear event
          </button>
        </fieldset>

        {/* Save button + feedback */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleSave}
            disabled={update.isPending}
            className="rounded-md bg-brand-600 px-6 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {update.isPending ? 'Saving…' : 'Save'}
          </button>

          {update.isSuccess && (
            <p className="text-sm text-success-600" role="status">
              Settings saved.
            </p>
          )}

          {update.isError && (
            <p className="text-sm text-danger-500" role="alert">
              {(update.error as { status?: number })?.status === 422
                ? 'Invalid data — check emails and try again (max 10).'
                : 'Save failed. Please try again.'}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
