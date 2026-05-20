import { useCallback, useState, type ReactNode } from 'react';
import { AnnounceContext } from './announce-context';

export function LiveRegion({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState('');
  const announce = useCallback((next: string) => {
    // Force change-detection even if same message is announced twice.
    setMsg('');
    setTimeout(() => setMsg(next), 0);
  }, []);
  return (
    <AnnounceContext.Provider value={announce}>
      {children}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {msg}
      </div>
    </AnnounceContext.Provider>
  );
}
