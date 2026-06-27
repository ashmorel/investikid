import { useSyncExternalStore } from 'react';
import { onlineManager } from '@tanstack/react-query';

function subscribe(onChange: () => void) {
  return onlineManager.subscribe(() => onChange());
}

function getSnapshot() {
  return onlineManager.isOnline();
}

/** True while TanStack's onlineManager reports connectivity (fed by
 * @capacitor/network — see lib/connectivity.ts). */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
