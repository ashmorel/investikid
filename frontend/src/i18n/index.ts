import i18n from 'i18next';
import type { Resource, ResourceLanguage } from 'i18next';
import { initReactI18next } from 'react-i18next';
import type { LanguageCode } from './languages';

const NAMESPACES = ['common'] as const;

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
  // Separator convention: nsSeparator=':' (default), keySeparator='.' (default).
  // Callers write feature-namespaced dotted keys, e.g. t('common.appName').
  // i18next resolves this as: namespace=defaultNS ('common'), key path = common → appName.
  // Catalog files therefore nest keys under their own namespace name:
  //   common.json: { "common": { "appName": "..." } }
  // This keeps call sites readable ("common.appName" not "appName") and lets
  // future namespaces (e.g. 'home') be added as home.json with nested keys.
  await i18n.use(initReactI18next).init({
    lng,
    fallbackLng: 'en',
    ns: [...NAMESPACES],
    defaultNS: 'common',
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
