import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../src/api/auth', () => ({
  authApi: { updateLanguage: vi.fn().mockResolvedValue({ language: 'es' }) },
}));
vi.mock('../../src/i18n', () => ({ changeLanguage: vi.fn().mockResolvedValue(undefined) }));

import { authApi } from '../../src/api/auth';
import { changeLanguage } from '../../src/i18n';
import { useLanguage } from '../../src/hooks/useLanguage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient();
  qc.setQueryData(['me'], { language: 'en' });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useLanguage', () => {
  beforeEach(() => localStorage.clear());

  it('reads current language from the cached profile', () => {
    const { result } = renderHook(() => useLanguage(), { wrapper });
    expect(result.current.current).toBe('en');
  });

  it('setLanguage updates i18n, localStorage and the server', async () => {
    const { result } = renderHook(() => useLanguage(), { wrapper });
    await act(async () => {
      await result.current.setLanguage('es');
    });
    expect(changeLanguage).toHaveBeenCalledWith('es');
    expect(localStorage.getItem('language')).toBe('es');
    await waitFor(() => expect(authApi.updateLanguage).toHaveBeenCalledWith('es'));
  });
});
