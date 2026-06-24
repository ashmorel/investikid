import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useAdminSettings,
  useUpdateAdminSettings,
  useGenerateTranslations,
  useTranslationCoverage,
} from '@/api/admin';
import { SUPPORTED_LANGUAGES } from '@/i18n/languages';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CONTENT_LANGUAGE_OPTIONS = SUPPORTED_LANGUAGES.filter((l) => l.code !== 'en');

export default function AdminSettings() {
  const { t } = useTranslation('admin');
  const { data, isLoading, isError: isLoadError } = useAdminSettings();
  const update = useUpdateAdminSettings();
  const generate = useGenerateTranslations();

  const [emails, setEmails] = useState<string[]>([]);
  const [contentLanguages, setContentLanguages] = useState<string[]>([]);
  const [genLanguage, setGenLanguage] = useState<string>(CONTENT_LANGUAGE_OPTIONS[0]?.code ?? '');
  const [coverageLanguage, setCoverageLanguage] = useState<string>('');
  const coverageQ = useTranslationCoverage(coverageLanguage);
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState('');
  const [eventTitle, setEventTitle] = useState('');
  const [eventEmoji, setEventEmoji] = useState('');
  const [eventStart, setEventStart] = useState('');
  const [eventEnd, setEventEnd] = useState('');
  const [eventBonus, setEventBonus] = useState(0);
  const [enrollBonus, setEnrollBonus] = useState(25);
  const [completionBonus, setCompletionBonus] = useState(250);
  // Seed local state once data arrives; seeded ref avoids re-seeding on invalidate/refetch
  const seeded = useRef(false);

  useEffect(() => {
    if (data && !seeded.current) {
      setEmails(data.alert_emails);
      setEnrollBonus(data.market_enroll_bonus_coins);
      setCompletionBonus(data.market_completion_bonus_coins);
      setContentLanguages(data.enabled_content_languages ?? []);
      if (data.seasonal_event) {
        /* eslint-disable react-hooks/set-state-in-effect -- one-shot, ref-guarded
           seeding of form fields from the fetched settings; mirrors the
           established alert_emails seeding pattern above. */
        setEventTitle(data.seasonal_event.title);
        setEventEmoji(data.seasonal_event.emoji);
        setEventStart(data.seasonal_event.starts_at.slice(0, 10));
        setEventEnd(data.seasonal_event.ends_at.slice(0, 10));
        setEventBonus(data.seasonal_event.xp_bonus_pct);
        /* eslint-enable react-hooks/set-state-in-effect */
      }
      seeded.current = true;
    }
  }, [data]);

  function handleAdd() {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      setInputError(t('settings.alertEmails.error.empty'));
      return;
    }
    if (!EMAIL_RE.test(trimmed)) {
      setInputError(t('settings.alertEmails.error.invalid'));
      return;
    }
    if (emails.includes(trimmed)) {
      setInputError(t('settings.alertEmails.error.duplicate'));
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
      market_enroll_bonus_coins: enrollBonus,
      market_completion_bonus_coins: completionBonus,
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

  function toggleContentLanguage(code: string) {
    setContentLanguages((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
    update.reset();
  }

  function handleSaveContentLanguages() {
    update.mutate({ alert_emails: emails, enabled_content_languages: contentLanguages });
  }

  function handleGenerate() {
    if (!genLanguage) return;
    generate.mutate({ language: genLanguage });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  }

  if (isLoading) {
    return <p className="p-6 text-muted-foreground">{t('layout.loading')}</p>;
  }

  if (isLoadError) {
    return <p className="p-6 text-danger-500">{t('settings.loadError')}</p>;
  }

  return (
    <div className="p-6 text-ink">
      <h1 className="mb-6 text-2xl font-bold text-ink">{t('settings.pageTitle')}</h1>

      <section aria-labelledby="alert-emails-heading" className="max-w-xl">
        <h2 id="alert-emails-heading" className="mb-1 text-lg font-semibold text-ink">
          {t('settings.alertEmails.heading')}
        </h2>
        <p className="mb-4 text-sm text-muted-foreground">
          {t('settings.alertEmails.description')}
        </p>

        {/* Add email row */}
        <div className="mb-4 flex gap-2">
          <div className="flex-1">
            <label htmlFor="new-alert-email" className="mb-1 block text-sm text-muted-foreground">
              {t('settings.alertEmails.addLabel')}
            </label>
            <input
              id="new-alert-email"
              type="email"
              value={inputValue}
              onChange={(e) => { setInputValue(e.target.value); setInputError(''); }}
              onKeyDown={handleKeyDown}
              placeholder={t('settings.alertEmails.placeholder')}
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
              {t('settings.alertEmails.addButton')}
            </button>
          </div>
        </div>

        {/* Email list */}
        {emails.length === 0 ? (
          <p className="mb-4 rounded-md border border-line bg-card px-4 py-3 text-sm text-muted-foreground">
            {t('settings.alertEmails.noRecipients')}
          </p>
        ) : (
          <ul aria-label={t('settings.alertEmails.recipientsList')} className="mb-4 flex flex-col gap-2">
            {emails.map((email) => (
              <li
                key={email}
                className="flex items-center justify-between rounded-md border border-line bg-card px-3 py-2"
              >
                <span className="text-sm text-ink">{email}</span>
                <button
                  type="button"
                  onClick={() => handleRemove(email)}
                  aria-label={t('settings.alertEmails.removeAriaLabel', { email })}
                  className="ml-3 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-brand-50 hover:text-danger-500 focus:outline-none focus:ring-1 focus:ring-danger-500"
                >
                  {t('settings.alertEmails.removeButton')}
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* Market reward bonuses (Sub-project D) — coins, live in AppSetting */}
        <fieldset className="mb-4 rounded-2xl border border-line bg-card p-5">
          <legend className="px-1 text-base font-extrabold text-ink">{t('settings.marketRewards.legend')}</legend>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="enroll-bonus" className="mb-1 block text-sm text-ink">{t('settings.marketRewards.enrollBonus')}</label>
              <input id="enroll-bonus" type="number" min={0} value={enrollBonus}
                onChange={(e) => setEnrollBonus(Number(e.target.value))}
                className="w-32 rounded-md border border-input bg-background px-3 py-2 text-base text-ink" />
            </div>
            <div>
              <label htmlFor="completion-bonus" className="mb-1 block text-sm text-ink">{t('settings.marketRewards.completionBonus')}</label>
              <input id="completion-bonus" type="number" min={0} value={completionBonus}
                onChange={(e) => setCompletionBonus(Number(e.target.value))}
                className="w-32 rounded-md border border-input bg-background px-3 py-2 text-base text-ink" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {t('settings.marketRewards.description')}
          </p>
        </fieldset>

        {/* Content languages (E1) — kill-switch for serving stored translations */}
        <fieldset className="mb-4 rounded-2xl border border-line bg-card p-5">
          <legend className="px-1 text-base font-extrabold text-ink">{t('settings.contentLanguages.legend')}</legend>
          <p className="mb-3 text-xs text-muted-foreground">{t('settings.contentLanguages.description')}</p>
          <div className="flex flex-wrap gap-3">
            {CONTENT_LANGUAGE_OPTIONS.map((lang) => (
              <label key={lang.code} className="flex items-center gap-2 text-sm text-ink">
                <input
                  type="checkbox"
                  checked={contentLanguages.includes(lang.code)}
                  onChange={() => toggleContentLanguage(lang.code)}
                  className="h-4 w-4 rounded border-input"
                />
                <span>{lang.endonym} ({lang.code})</span>
              </label>
            ))}
          </div>
          <button
            type="button"
            onClick={handleSaveContentLanguages}
            disabled={update.isPending}
            className="mt-3 rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {t('settings.contentLanguages.save')}
          </button>
        </fieldset>

        {/* Translations (E1) — generate batches + coverage view */}
        <fieldset className="mb-4 rounded-2xl border border-line bg-card p-5">
          <legend className="px-1 text-base font-extrabold text-ink">{t('settings.translations.legend')}</legend>
          <p className="mb-3 text-xs text-muted-foreground">{t('settings.translations.generateDescription')}</p>
          <div className="mb-2 flex items-end gap-2">
            <div>
              <label htmlFor="gen-language" className="mb-1 block text-sm text-ink">{t('settings.translations.languageLabel')}</label>
              <select
                id="gen-language"
                value={genLanguage}
                onChange={(e) => setGenLanguage(e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-base text-ink"
              >
                {CONTENT_LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.code} value={lang.code}>{lang.endonym} ({lang.code})</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={generate.isPending || !genLanguage}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {generate.isPending ? t('settings.translations.generating') : t('settings.translations.generate')}
            </button>
          </div>
          {generate.isSuccess && generate.data && (
            <p className="text-sm text-success-600" role="status">
              {t('settings.translations.result', {
                translated: generate.data.translated,
                skipped: generate.data.skipped_fresh,
                failed: generate.data.failed,
              })}
            </p>
          )}
          {generate.isError && (
            <p className="text-sm text-danger-500" role="alert">{t('settings.translations.generateError')}</p>
          )}

          <h3 className="mt-4 mb-2 text-sm font-semibold text-ink">{t('settings.translations.coverageHeading')}</h3>
          <div className="mb-2 flex items-end gap-2">
            <div>
              <label htmlFor="cov-language" className="mb-1 block text-sm text-ink">{t('settings.translations.languageLabel')}</label>
              <select
                id="cov-language"
                value={coverageLanguage}
                onChange={(e) => setCoverageLanguage(e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-base text-ink"
              >
                {CONTENT_LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang.code} value={lang.code}>{lang.endonym} ({lang.code})</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => setCoverageLanguage((c) => c || CONTENT_LANGUAGE_OPTIONS[0]?.code || '')}
              className="rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50"
            >
              {t('settings.translations.loadCoverage')}
            </button>
          </div>
          {coverageQ.isError && (
            <p className="text-sm text-danger-500" role="alert">{t('settings.translations.coverageError')}</p>
          )}
          {coverageQ.data && (
            <table className="mt-2 w-full text-sm text-ink">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1 pr-4" scope="col">{coverageQ.data.language}</th>
                  <th className="py-1 pr-4" scope="col">{t('settings.translations.colActive')}</th>
                  <th className="py-1 pr-4" scope="col">{t('settings.translations.colFailed')}</th>
                  <th className="py-1" scope="col">{t('settings.translations.colMissing')}</th>
                </tr>
              </thead>
              <tbody>
                {([
                  ['entityModules', coverageQ.data.modules],
                  ['entityLevels', coverageQ.data.levels],
                  ['entityLessons', coverageQ.data.lessons],
                ] as const).map(([labelKey, bucket]) => (
                  <tr key={labelKey} className="border-t border-line">
                    <th className="py-1 pr-4 text-left font-medium" scope="row">{t(`settings.translations.${labelKey}`)}</th>
                    <td className="py-1 pr-4">{bucket.active}</td>
                    <td className="py-1 pr-4">{bucket.failed}</td>
                    <td className="py-1">{bucket.missing}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </fieldset>

        {/* Seasonal event (M9) — deploy-free, lives in AppSetting */}
        <fieldset className="mb-4 rounded-2xl border border-line bg-card p-5">
          <legend className="px-1 text-base font-extrabold text-ink">{t('settings.seasonalEvent.legend')}</legend>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label htmlFor="ev-title" className="mb-1 block text-sm text-ink">{t('settings.seasonalEvent.title')}</label>
              <input id="ev-title" value={eventTitle} maxLength={60} onChange={(e) => setEventTitle(e.target.value)}
                placeholder={t('settings.seasonalEvent.titlePlaceholder')}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-emoji" className="mb-1 block text-sm text-ink">{t('settings.seasonalEvent.emoji')}</label>
              <input id="ev-emoji" value={eventEmoji} maxLength={8} onChange={(e) => setEventEmoji(e.target.value)}
                placeholder="🎃" className="w-24 rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-bonus" className="mb-1 block text-sm text-ink">{t('settings.seasonalEvent.bonusXp')}</label>
              <input id="ev-bonus" type="number" min={0} max={100} value={eventBonus}
                onChange={(e) => setEventBonus(Number(e.target.value))}
                className="w-24 rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-start" className="mb-1 block text-sm text-ink">{t('settings.seasonalEvent.starts')}</label>
              <input id="ev-start" type="date" value={eventStart} onChange={(e) => setEventStart(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
            <div>
              <label htmlFor="ev-end" className="mb-1 block text-sm text-ink">{t('settings.seasonalEvent.ends')}</label>
              <input id="ev-end" type="date" value={eventEnd} onChange={(e) => setEventEnd(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-ink" />
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {t('settings.seasonalEvent.description')}
          </p>
          <button
            type="button"
            onClick={() => {
              setEventTitle(''); setEventEmoji(''); setEventStart(''); setEventEnd(''); setEventBonus(0);
              update.mutate({ alert_emails: emails, clear_seasonal_event: true });
            }}
            className="mt-2 rounded-md border border-line px-3 py-1.5 text-xs text-muted-foreground hover:bg-brand-50"
          >
            {t('settings.seasonalEvent.clearButton')}
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
            {update.isPending ? t('settings.saving') : t('settings.save')}
          </button>

          {update.isSuccess && (
            <p className="text-sm text-success-600" role="status">
              {t('settings.saveSuccess')}
            </p>
          )}

          {update.isError && (
            <p className="text-sm text-danger-500" role="alert">
              {(update.error as { status?: number })?.status === 422
                ? t('settings.saveErrorInvalid')
                : t('settings.saveErrorGeneric')}
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
