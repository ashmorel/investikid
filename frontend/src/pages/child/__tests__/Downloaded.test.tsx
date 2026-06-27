// frontend/src/pages/child/__tests__/Downloaded.test.tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('@/lib/offline/sqlite', () => ({
  isOfflineDbAvailable: vi.fn(() => true),
}));

type DownloadedRow = { levelId: string; title: string; lessonCount: number };
const mockListDownloaded: ReturnType<typeof vi.fn<() => Promise<DownloadedRow[]>>> = vi.fn(
  async () => [] as DownloadedRow[],
);
const mockRemoveLevel: ReturnType<typeof vi.fn<() => Promise<void>>> = vi.fn(async () => undefined);

vi.mock('@/lib/offline/contentStore', () => ({
  listDownloadedLevels: (_scope: unknown) => mockListDownloaded(),
  removeLevel: (scope: unknown, levelId: unknown) => (mockRemoveLevel as (s: unknown, l: unknown) => Promise<void>)(scope, levelId),
}));

import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import Downloaded from '../Downloaded';

function renderPage(levels?: { levelId: string; title: string; lessonCount: number }[]) {
  if (levels) mockListDownloaded.mockResolvedValue(levels);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['me'], { id: 'C1', active_market_code: 'GB' });
  return {
    qc,
    ...render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <Downloaded />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(isOfflineDbAvailable).mockReturnValue(true);
  mockListDownloaded.mockResolvedValue([]);
});

describe('Downloaded page', () => {
  it('shows the page title', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument());
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Downloaded');
  });

  it('renders empty state when no levels are saved', async () => {
    renderPage([]);
    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Nothing saved yet'),
    );
    expect(screen.getByText(/open a level and tap download/i)).toBeInTheDocument();
  });

  it('renders a row per downloaded level with title and lesson count', async () => {
    renderPage([
      { levelId: 'LV1', title: 'Intro to Stocks', lessonCount: 5 },
      { levelId: 'LV2', title: 'Risk Basics', lessonCount: 2 },
    ]);
    await waitFor(() => expect(screen.getByText('Intro to Stocks')).toBeInTheDocument());
    expect(screen.getByText('Risk Basics')).toBeInTheDocument();
    expect(screen.getByText('5 lessons saved')).toBeInTheDocument();
    expect(screen.getByText('2 lessons saved')).toBeInTheDocument();
  });

  it('singular lesson count says "1 lesson saved"', async () => {
    renderPage([{ levelId: 'LV1', title: 'Basics', lessonCount: 1 }]);
    await waitFor(() => expect(screen.getByText('1 lesson saved')).toBeInTheDocument());
  });

  it('remove button calls removeLevel and invalidates queries', async () => {
    const { qc } = renderPage([
      { levelId: 'LV1', title: 'Intro to Stocks', lessonCount: 5 },
    ]);
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    await waitFor(() => expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /remove/i }));
    await waitFor(() => expect(mockRemoveLevel).toHaveBeenCalledWith(
      { childId: 'C1', market: 'GB' },
      'LV1',
    ));
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['downloaded-levels'] }));
    expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ['offline-availability'] }));
  });

  it('has no axe violations in populated state', async () => {
    const { container } = renderPage([
      { levelId: 'LV1', title: 'Intro to Stocks', lessonCount: 5 },
    ]);
    await waitFor(() => expect(screen.getByText('Intro to Stocks')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no axe violations in empty state', async () => {
    const { container } = renderPage([]);
    await waitFor(() =>
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Nothing saved yet'),
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
