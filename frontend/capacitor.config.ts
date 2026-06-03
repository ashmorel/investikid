import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'leeashmore.investikid.ai.app',
  appName: 'InvestiKid',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    // Route fetch/XHR through native HTTP so cross-origin auth cookies
    // (set by the Railway API) persist on iOS WKWebView, which otherwise
    // drops them as third-party. CapacitorCookies keeps document.cookie
    // working so the CSRF double-submit token can still be read in JS.
    CapacitorHttp: {
      enabled: true,
    },
    CapacitorCookies: {
      enabled: true,
    },
  },
};

export default config;
