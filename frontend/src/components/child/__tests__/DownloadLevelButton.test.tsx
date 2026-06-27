// frontend/src/components/child/__tests__/DownloadLevelButton.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ─── mocks (hoisted before any imports that consume them) ───────────────────
vi.mock('@/lib/offline/sqlite', () => ({
  isOfflineDbAvailable: vi.fn(() => true),
}));

vi.mock('@/lib/offline/contentStore', () => ({
  upsertLesson: vi.fn(async () => {}),
  listAvailableOffline: vi.fn(async () => ({ levelIds: [], lessonCount: 0 })),
}));

vi.mock('@/hooks/useOnline', () => ({
  useOnline: vi.fn(() => true),
}));

vi.mock('@/hooks/useOfflineAvailability', () => ({
  useOfflineAvailability: vi.fn(() => ({ levelIds: new Set<string>(), lessonCount: 0 })),
}));

vi.mock('@/api/content', () => ({
  contentApi: {
    getLesson: vi.fn(async (id: string) => ({
      id,
      module_id: 'mod1',
      type: 'card' as const,
      content_json: {},
      xp_reward: 10,
      order_index: 0,
      completed: false,
      locked: false,
    })),
  },
}));

// ─── imports after mocks ────────────────────────────────────────────────────
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { upsertLesson } from '@/lib/offline/contentStore';
import { useOnline } from '@/hooks/useOnline';
import { useOfflineAvailability } from '@/hooks/useOfflineAvailability';
import { contentApi } from '@/api/content';
import { DownloadLevelButton } from '../DownloadLevelButton';
import type { LessonSummary } from '@/api/content';

const mockIsAvailable = vi.mocked(isOfflineDbAvailable);
const mockUpsert = vi.mocked(upsertLesson);
const mockUseOnline = vi.mocked(useOnline);
const mockUseOfflineAvailability = vi.mocked(useOfflineAvailability);
const mockGetLesson = vi.mocked(contentApi.getLesson);

const LESSONS: LessonSummary[] = [
  { id: 'L1', type: 'card', title: 'Lesson 1', xp_reward: 10, order_index: 0, completed: false },
  { id: 'L2', type: 'card', title: 'Lesson 2', xp_reward: 10, order_index: 1, completed: false },
];

function makeQc(meData?: object) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (meData !== undefined) {
    qc.setQueryData(['me'], meData);
  } else {
    qc.setQueryData(['me'], { id: 'C1', active_market_code: 'GB' });
  }
  return qc;
}

function renderBtn(levelId = 'LV1', lessons = LESSONS, qc?: QueryClient) {
  const client = qc ?? makeQc();
  return render(
    <QueryClientProvider client={client}>
      <DownloadLevelButton levelId={levelId} lessons={lessons} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsAvailable.mockReturnValue(true);
  mockUseOnline.mockReturnValue(true);
  mockUseOfflineAvailability.mockReturnValue({ levelIds: new Set(), lessonCount: 0 });
  mockGetLesson.mockImplementation(async (id: string) => ({
    id,
    module_id: 'mod1',
    type: 'card' as const,
    content_json: {},
    xp_reward: 10,
    order_index: 0,
    completed: false,
    locked: false,
  }));
  mockUpsert.mockResolvedValue(undefined);
});

// ─── tests ──────────────────────────────────────────────────────────────────

describe('DownloadLevelButton', () => {
  it('renders nothing when isOfflineDbAvailable() is false', () => {
    mockIsAvailable.mockReturnValue(false);
    const { container } = renderBtn();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when scope is null (no me in cache)', () => {
    // Pass a qc with no ['me'] data
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = renderBtn('LV1', LESSONS, qc);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when offline and level not yet saved', () => {
    mockUseOnline.mockReturnValue(false);
    mockUseOfflineAvailability.mockReturnValue({ levelIds: new Set(), lessonCount: 0 });
    const { container } = renderBtn();
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the download button when online and not yet saved', () => {
    renderBtn();
    expect(screen.getByRole('button', { name: /download for offline/i })).toBeInTheDocument();
  });

  it('shows "Available offline" status when level is already saved', () => {
    mockUseOfflineAvailability.mockReturnValue({ levelIds: new Set(['LV1']), lessonCount: 2 });
    renderBtn();
    expect(screen.getByRole('status')).toHaveTextContent(/available offline/i);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('shows "Available offline" status even when offline, if already saved', () => {
    mockUseOnline.mockReturnValue(false);
    mockUseOfflineAvailability.mockReturnValue({ levelIds: new Set(['LV1']), lessonCount: 2 });
    renderBtn();
    expect(screen.getByRole('status')).toHaveTextContent(/available offline/i);
  });

  it('clicking ingests all lessons and calls upsertLesson per lesson', async () => {
    renderBtn();
    const btn = screen.getByRole('button', { name: /download for offline/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(mockGetLesson).toHaveBeenCalledTimes(LESSONS.length);
    });
    expect(mockGetLesson).toHaveBeenCalledWith('L1');
    expect(mockGetLesson).toHaveBeenCalledWith('L2');

    await waitFor(() => {
      expect(mockUpsert).toHaveBeenCalledTimes(LESSONS.length);
    });
    expect(mockUpsert).toHaveBeenCalledWith(
      { childId: 'C1', market: 'GB' },
      expect.objectContaining({ id: 'L1' }),
      'LV1',
    );
    expect(mockUpsert).toHaveBeenCalledWith(
      { childId: 'C1', market: 'GB' },
      expect.objectContaining({ id: 'L2' }),
      'LV1',
    );
  });

  it('shows progress text while downloading', async () => {
    // Use only one lesson so the blocked promise controls the whole download
    const singleLesson: LessonSummary[] = [LESSONS[0]];
    let resolveLesson!: () => void;
    mockGetLesson.mockImplementationOnce(
      () =>
        new Promise<{ id: string; module_id: string; type: 'card'; content_json: Record<string, unknown>; xp_reward: number; order_index: number; completed: boolean; locked: boolean }>((resolve) => {
          resolveLesson = () =>
            resolve({
              id: 'L1',
              module_id: 'mod1',
              type: 'card',
              content_json: {},
              xp_reward: 10,
              order_index: 0,
              completed: false,
              locked: false,
            });
        }),
    );

    renderBtn('LV1', singleLesson);
    fireEvent.click(screen.getByRole('button', { name: /download for offline/i }));

    // While the lesson is pending, the progress status is visible
    await waitFor(() => {
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
    expect(screen.getByRole('status')).toHaveTextContent(/saving lessons/i);

    // Unblock the promise
    resolveLesson();
    await waitFor(() => expect(mockUpsert).toHaveBeenCalledTimes(1));
  });

  it('invalidates ["offline-availability"] after download completes', async () => {
    const qc = makeQc();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    renderBtn('LV1', LESSONS, qc);

    fireEvent.click(screen.getByRole('button', { name: /download for offline/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: ['offline-availability'] }),
      );
    });
  });

  it('disables the button (no double-click) while downloading', async () => {
    let resolveLesson: () => void;
    mockGetLesson.mockImplementationOnce(
      () =>
        new Promise<{ id: string; module_id: string; type: 'card'; content_json: Record<string, unknown>; xp_reward: number; order_index: number; completed: boolean; locked: boolean }>((resolve) => {
          resolveLesson = () =>
            resolve({
              id: 'L1',
              module_id: 'mod1',
              type: 'card',
              content_json: {},
              xp_reward: 10,
              order_index: 0,
              completed: false,
              locked: false,
            });
        }),
    );

    renderBtn('LV1', [LESSONS[0]]);
    fireEvent.click(screen.getByRole('button', { name: /download for offline/i }));

    // Button should be gone while busy (progress UI shows instead)
    await waitFor(() => {
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    resolveLesson!();
  });

  it('idle state has no axe violations', async () => {
    const { container } = renderBtn();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('saved state has no axe violations', async () => {
    mockUseOfflineAvailability.mockReturnValue({ levelIds: new Set(['LV1']), lessonCount: 2 });
    const { container } = renderBtn();
    expect(await axe(container)).toHaveNoViolations();
  });
});
