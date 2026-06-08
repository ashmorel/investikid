import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeApp, isAndroid } from './platform';

// Sky-blue brand surface behind the status bar (matches theme-color).
const STATUS_BAR_BG = '#38bdf8';

/** Configure native status bar / edge-to-edge. No-op on web. */
export async function initNativeChrome(): Promise<void> {
  if (!isNativeApp()) return;
  try {
    await StatusBar.setOverlaysWebView({ overlay: true });
    await StatusBar.setStyle({ style: Style.Light });
    if (isAndroid()) {
      await StatusBar.setBackgroundColor({ color: STATUS_BAR_BG });
    }
  } catch {
    // StatusBar can throw on unsupported surfaces; non-fatal.
  }
}
