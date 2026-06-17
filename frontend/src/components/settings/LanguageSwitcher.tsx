import { useTranslation } from 'react-i18next';
import { useLanguage } from '../../hooks/useLanguage';
import { AVAILABLE_LANGUAGES, type LanguageCode } from '../../i18n/languages';

export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { current, setLanguage } = useLanguage();

  return (
    <div className="space-y-1.5">
      <label htmlFor="settings-language" className="text-sm font-medium">
        {t('language.label')}
      </label>
      <select
        id="settings-language"
        value={current}
        onChange={(e) => void setLanguage(e.target.value as LanguageCode)}
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-base"
      >
        {AVAILABLE_LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.endonym}
          </option>
        ))}
      </select>
      <p className="text-xs text-muted-foreground">{t('language.help')}</p>
    </div>
  );
}
