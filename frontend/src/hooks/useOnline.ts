import { useSyncExternalStore } from 'react';

function subscribe(onChange: () => void) {
  window.addEventListener('online', onChange);
  window.addEventListener('offline', onChange);
  return () => {
    window.removeEventListener('online', onChange);
    window.removeEventListener('offline', onChange);
  };
}

function getSnapshot() {
  return navigator.onLine;
}

/** True while the browser reports network connectivity. */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot);
}
