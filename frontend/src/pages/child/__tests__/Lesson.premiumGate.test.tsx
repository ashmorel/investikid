import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Lesson from '../Lesson';
import { ApiError } from '@/api/client';
import { contentApi, type LessonOut } from '@/api/content';

const openPaywall = vi.fn();
const toast = vi.fn();

vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open: openPaywall }) }));
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast }) }));
vi.mock('@/hooks/useActiveMissions', () => ({ useActiveMissions: () => ({ data: [] }) }));
vi.mock('@/hooks/useMarkets', () => ({ useMarkets: () => ({ data: [] }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

// Stub the heavy lesson widgets; this test targets the completion path only.
// CardLesson exposes a Complete button that drives the page's onComplete handler.
vi.mock('@/components/child/lesson/CardLesson', () => ({
  CardLesson: ({ onComplete }: { onComplete: (score: number | null) => void }) => (
    <button onClick={() => onComplete(null)}>Complete lesson</button>
  ),
}));
vi.mock('@/components/child/lesson/QuizLesson', () => ({ QuizLesson: () => null }));
vi.mock('@/components/child/lesson/ScenarioLesson', () => ({ ScenarioLesson: () => null }));
vi.mock('@/components/child/lesson/VideoLesson', () => ({ VideoLesson: () => null }));
vi.mock('@/components/child/lesson/CompletionPanel', () => ({ CompletionPanel: () => null }));
vi.mock('@/components/child/lesson/LessonIllustration', () => ({ LessonIllustration: () => null }));
vi.mock('@/components/child/lesson/PracticeQuiz', () => ({ PracticeQuiz: () => null }));
vi.mock('@/components/child/lesson/CoachPennyPanel', () => ({ CoachPennyPanel: () => null }));
vi.mock('@/components/child/lesson/LessonChrome', () => ({ LessonChrome: () => null }));
vi.mock('@/components/child/lesson/ApplyMissionCTA', () => ({ ApplyMissionCTA: () => null }));
vi.mock('@/components/child/MachineTranslatedBadge', () => ({ MachineTranslatedBadge: () => null }));

const LESSON: LessonOut = {
  id: 'lesson-1',
  module_id: 'mod-1',
  type: 'card',
  content_json: { title: 'Saving basics', body: 'Body' },
  xp_reward: 5,
  order_index: 0,
  completed: false,
  locked: false,
};

vi.mock('@/api/content', () => ({
  contentApi: {
    getLesson: vi.fn(),
    listLevelLessons: vi.fn(() => Promise.resolve([])),
    listModules: vi.fn(() => Promise.resolve([])),
    listLevels: vi.fn(() => Promise.resolve([])),
    completeLesson: vi.fn(),
    recordLessonView: vi.fn(() => Promise.resolve(null)),
  },
}));

const mockGetLesson = vi.mocked(contentApi.getLesson);
const mockComplete = vi.mocked(contentApi.completeLesson);

function renderLesson() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/lessons/mod-1/level-1/lesson-1']}>
        <Routes>
          <Route path="/lessons/:moduleId/:levelId/:lessonId" element={<Lesson />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Lesson completion — multi-market premium gate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetLesson.mockResolvedValue(LESSON);
  });

  it('opens the paywall (kind: home) instead of the generic toast on premium_required', async () => {
    const user = userEvent.setup();
    mockComplete.mockRejectedValue(
      new ApiError(403, 'Premium required', 'premium_required', { kind: 'market', label: 'United States' }),
    );
    renderLesson();

    await user.click(await screen.findByRole('button', { name: /Complete lesson/i }));

    await waitFor(() => expect(openPaywall).toHaveBeenCalledTimes(1));
    expect(openPaywall).toHaveBeenCalledWith({ kind: 'home', label: 'United States' });
    // The generic save-error toast must NOT fire for the premium case.
    expect(toast).not.toHaveBeenCalledWith(
      expect.objectContaining({ title: 'lesson.saveError' }),
    );
  });

  it('still shows the generic save-error toast for non-premium errors', async () => {
    const user = userEvent.setup();
    mockComplete.mockRejectedValue(new Error('boom'));
    renderLesson();

    await user.click(await screen.findByRole('button', { name: /Complete lesson/i }));

    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith({ title: 'lesson.saveError', description: 'lesson.tryAgain' }),
    );
    expect(openPaywall).not.toHaveBeenCalled();
  });
});
