import { onlineManager } from '@tanstack/react-query';
import { Network } from '@capacitor/network';

/**
 * Feed TanStack Query's onlineManager from @capacitor/network. On iOS WKWebView
 * navigator.onLine is unreliable; the native plugin uses the OS connectivity
 * API (and a web implementation on the web build). Wiring onlineManager makes
 * queries pause offline and auto-refetch stale data on reconnect. Best-effort:
 * any failure leaves onlineManager on its navigator.onLine-based default.
 */
export async function initConnectivity(): Promise<void> {
  try {
    const status = await Network.getStatus();
    onlineManager.setOnline(status.connected);
    void Network.addListener('networkStatusChange', (s) => {
      onlineManager.setOnline(s.connected);
    });
  } catch {
    // plugin unavailable — keep onlineManager's default detection
  }
}
