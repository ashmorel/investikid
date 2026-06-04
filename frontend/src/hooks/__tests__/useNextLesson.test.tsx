import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useNextLesson } from '../useNextLesson';
import { contentApi } from '@/api/content';

vi.mock('@/api/content', async (orig) => {
  const actual = await orig<typeof import('@/api/content')>();
  return { ...actual, contentApi: { ...actual.contentApi, nextLesson: vi.fn() } };
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useNextLesson', () => {
  it('maps a resolved lesson to start/continue with a deep-link', async () => {
    (contentApi.nextLesson as ReturnType<typeof vi.fn>).mockResolvedValue({
      next: { module_id: 'm1', module_title: 'Mod', module_icon: '📈', level_id: 'l1', lesson_id: 'q1', lesson_title: 'Intro', mode: 'start' },
    });
    const { result } = renderHook(() => useNextLesson(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.mode).toBe('start');
    expect(result.current.to).toBe('/lessons/m1/l1/q1');
    expect(result.current.lessonLabel).toBe('Intro');
  });

  it('reports caught_up when resolver returns null', async () => {
    (contentApi.nextLesson as ReturnType<typeof vi.fn>).mockResolvedValue({ next: null });
    const { result } = renderHook(() => useNextLesson(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.mode).toBe('caught_up');
    expect(result.current.to).toBeNull();
  });
});
