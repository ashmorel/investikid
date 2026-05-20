import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';

import { CardLesson } from '@/components/child/lesson/CardLesson';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { PracticeQuiz } from '@/components/child/lesson/PracticeQuiz';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('a11y: lesson renderers', () => {
  it('CardLesson has no axe violations', async () => {
    const { container } = wrap(
      <CardLesson contentJson={{ title: 'A stock', body: 'Body text' }} onComplete={() => {}} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('QuizLesson has no axe violations', async () => {
    const { container } = wrap(
      <QuizLesson
        contentJson={{
          question: 'Q?',
          choices: ['A', 'B', 'C', 'D'],
          answer_index: 2,
          explanation: 'Because C.',
        }}
        onComplete={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ScenarioLesson has no axe violations', async () => {
    const { container } = wrap(
      <ScenarioLesson
        contentJson={{
          prompt: 'P?',
          choices: [
            { label: 'A', outcome: 'oA' },
            { label: 'B', outcome: 'oB' },
          ],
          correct_index: 1,
        }}
        onComplete={() => {}}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('VideoLesson (no youtube_id fallback) has no axe violations', async () => {
    const { container } = wrap(
      <VideoLesson contentJson={{}} onComplete={() => {}} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('PracticeQuiz (Challenge variant) has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          question: 'Q?',
          choices: ['A', 'B', 'C', 'D'],
          answer_index: 2,
          explanation: 'Because C.',
          variant_rung: 'harder',
        }),
        { status: 200 },
      ) as never,
    );
    const { container } = wrap(
      <PracticeQuiz lessonId="L1" onClose={() => {}} />,
    );
    await waitFor(() => expect(screen.getByText(/Challenge/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('PracticeQuiz (Warm-up variant) has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          question: 'Q?',
          choices: ['A', 'B', 'C', 'D'],
          answer_index: 2,
          explanation: 'Because C.',
          variant_rung: 'easier',
        }),
        { status: 200 },
      ) as never,
    );
    const { container } = wrap(
      <PracticeQuiz lessonId="L2" onClose={() => {}} />,
    );
    await waitFor(() => expect(screen.getByText(/Warm-up/)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
