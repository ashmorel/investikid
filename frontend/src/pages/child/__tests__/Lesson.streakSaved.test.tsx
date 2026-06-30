import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Lesson from '../Lesson';
import { contentApi, type LessonOut, type LessonCompletionResult } from '@/api/content';

const toast = vi.fn();
const maybeRequestReview = vi.fn();

vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open: vi.fn() }) }));
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast }) }));
vi.mock('@/hooks/useActiveMissions', () => ({ useActiveMissions: () => ({ data: [] }) }));
vi.mock('@/hooks/useMarkets', () => ({ useMarkets: () => ({ data: [] }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
vi.mock('@/lib/marketReward', () => ({ formatRewardToast: () => '' }));
vi.mock('@/lib/inAppReview', () => ({
  maybeRequestReview: (...args: unknown[]) => maybeRequestReview(...args),
  reviewSignalForCompletion: () => null,
}));

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

function result(over: Partial<LessonCompletionResult>): LessonCompletionResult {
  return {
    xp_awarded: 5,
    already_completed: false,
    total_xp: 100,
    level: 2,
    streak_count: 5,
    streak_freezes: 0,
    practice_available: false,
    reward: { coins: 0 } as never,
    ...over,
  };
}

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

describe('Lesson — streak-saved celebration (B6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetLesson.mockResolvedValue(LESSON);
  });

  it('fires the streak-saved toast when freeze_used is true', async () => {
    const user = userEvent.setup();
    mockComplete.mockResolvedValue(result({ freeze_used: true }));
    renderLesson();
    await user.click(await screen.findByRole('button', { name: /Complete lesson/i }));
    await waitFor(() =>
      expect(toast).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'lesson.streakSaved.title' }),
      ),
    );
  });

  it('does NOT fire the streak-saved toast when freeze_used is false', async () => {
    const user = userEvent.setup();
    mockComplete.mockResolvedValue(result({ freeze_used: false }));
    renderLesson();
    await user.click(await screen.findByRole('button', { name: /Complete lesson/i }));
    await waitFor(() => expect(mockComplete).toHaveBeenCalled());
    expect(toast).not.toHaveBeenCalledWith(
      expect.objectContaining({ title: 'lesson.streakSaved.title' }),
    );
  });

  it('does NOT fire the streak-saved toast when already_completed', async () => {
    const user = userEvent.setup();
    mockComplete.mockResolvedValue(result({ freeze_used: true, already_completed: true }));
    renderLesson();
    await user.click(await screen.findByRole('button', { name: /Complete lesson/i }));
    await waitFor(() => expect(mockComplete).toHaveBeenCalled());
    expect(toast).not.toHaveBeenCalledWith(
      expect.objectContaining({ title: 'lesson.streakSaved.title' }),
    );
  });
});
