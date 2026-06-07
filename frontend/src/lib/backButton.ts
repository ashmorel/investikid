import { App } from '@capacitor/app';
import { isNativeApp } from './platform';

/** Routes considered "top level" — pressing back here exits the app. */
export const ROOT_PATHS = ['/', '/home', '/parent', '/parent/login'] as const;

export type BackAction = 'back' | 'exit';

/** Pure decision: go back in history, or exit the app. */
export function decideBackAction(args: { path: string; canGoBack: boolean }): BackAction {
  const atRoot = (ROOT_PATHS as readonly string[]).includes(args.path);
  if (!atRoot) return 'back';
  return args.canGoBack ? 'back' : 'exit';
}

/** Wire the Android hardware back button. No-op on web/iOS. */
export function registerBackButton(): void {
  if (!isNativeApp()) return;
  App.addListener('backButton', ({ canGoBack }) => {
    const action = decideBackAction({ path: window.location.pathname, canGoBack });
    if (action === 'exit') {
      App.exitApp();
    } else {
      window.history.back();
    }
  });
}
