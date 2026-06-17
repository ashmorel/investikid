import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import type { Me } from '../api/auth';
import { authApi } from '../api/auth';
import { changeLanguage } from '../i18n';
import { LANGUAGE_STORAGE_KEY } from '../i18n/constants';
import { type LanguageCode, isSupportedLanguage } from '../i18n/languages';

export { LANGUAGE_STORAGE_KEY };

function resolveLanguage(me: Me | undefined): LanguageCode {
  if (me?.language && isSupportedLanguage(me.language)) {
    return me.language;
  }
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && isSupportedLanguage(stored)) {
    return stored;
  }
  return 'en';
}

export function useLanguage() {
  const qc = useQueryClient();
  const me = qc.getQueryData<Me>(['me']);
  const current: LanguageCode = resolveLanguage(me);

  const setLanguage = useCallback(
    async (lng: LanguageCode) => {
      await changeLanguage(lng); // instant UI swap
      localStorage.setItem(LANGUAGE_STORAGE_KEY, lng); // fast boot next time
      qc.setQueryData<Me | undefined>(['me'], (prev) =>
        prev ? { ...prev, language: lng } : prev,
      );
      try {
        await authApi.updateLanguage(lng); // server = source of truth
        void qc.invalidateQueries({ queryKey: ['me'] });
      } catch {
        // keep the local change; server reconciles on next /me load
      }
    },
    [qc],
  );

  return { current, setLanguage };
}
