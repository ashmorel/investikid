import i18n from 'i18next';
import type { Resource, ResourceLanguage } from 'i18next';
import { initReactI18next } from 'react-i18next';
import type { LanguageCode } from './languages';

const NAMESPACES = ['common', 'settings'] as const;

// Statically-analyzable glob so Vite can tree-shake and bundle locale JSON
// files properly. A fully-dynamic template-literal import would fail at build
// time because Vite cannot determine the chunk graph statically.
const localeModules = import.meta.glob('../locales/*/*.json') as Record<
  string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  () => Promise<{ default: Record<string, any> }>
>;

async function loadCatalog(lng: LanguageCode): Promise<ResourceLanguage> {
  const entries = await Promise.all(
    NAMESPACES.map(async (ns) => {
      const key = `../locales/${lng}/${ns}.json`;
      try {
        const loader = localeModules[key];
        if (!loader) return [ns, {}] as const;
        const mod = await loader();
        return [ns, mod.default] as const;
      } catch {
        return [ns, {}] as const;
      }
    }),
  );
  return Object.fromEntries(entries) as ResourceLanguage;
}

export async function initI18n(lng: LanguageCode): Promise<void> {
  // If already initialised, just switch language (avoids re-init error).
  if (i18n.isInitialized) {
    await changeLanguage(lng);
    return;
  }
  const resources: Resource = { [lng]: await loadCatalog(lng) };
  if (lng !== 'en') {
    resources.en = await loadCatalog('en');
  }
  // ── Locked key convention ────────────────────────────────────────────────
  // defaultNS = 'common'. Strings in common.json are accessed WITHOUT a prefix:
  //   t('appName')            → common.json root key "appName"
  //   t('language.label')     → common.json nested key language.label
  //
  // Feature namespaces are separate JSON files loaded on demand.  Components
  // call `useTranslation('<ns>')` and use relative keys:
  //   const { t } = useTranslation('home');
  //   t('hero.title')         → home.json key hero.title
  //
  // Cross-namespace access uses the ns:key form (nsSeparator = ':'):
  //   t('common:appName')     → common.json key appName, from any namespace
  //
  // keySeparator = '.' (default) — nested JSON objects use dot paths.
  // nsSeparator  = ':' (default) — explicit namespace override prefix.
  // Both are set explicitly below so the behaviour is visible at a glance.
  // ─────────────────────────────────────────────────────────────────────────
  await i18n.use(initReactI18next).init({
    lng,
    fallbackLng: 'en',
    ns: [...NAMESPACES],
    defaultNS: 'common',
    nsSeparator: ':',
    keySeparator: '.',
    resources,
    interpolation: { escapeValue: false },
    returnNull: false,
  });
}

export async function changeLanguage(lng: LanguageCode): Promise<void> {
  if (!i18n.hasResourceBundle(lng, 'common')) {
    const catalog = await loadCatalog(lng);
    for (const [ns, bundle] of Object.entries(catalog)) {
      i18n.addResourceBundle(lng, ns, bundle, true, true);
    }
  }
  await i18n.changeLanguage(lng);
}

export { i18n };
