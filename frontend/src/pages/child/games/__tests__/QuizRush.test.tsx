import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import QuizRush from '../QuizRush';
import * as api from '@/api/arcade';

vi.mock('@/api/arcade');

beforeEach(() => {
  vi.mocked(api.getQuizRushSession).mockResolvedValue({
    items: [
      { lesson_id: 'a', question: 'What is saving?', choices: ['Keeping money', 'Spending all'], answer_index: 0 },
    ],
  });
  vi.mocked(api.submitQuizRushScore).mockResolvedValue({
    points: 15, coins_awarded: 1, personal_best: 15, leaderboard_rank: 1,
  });
});

describe('QuizRush', () => {
  it('plays a question and reaches results', async () => {
    render(<MemoryRouter><QuizRush /></MemoryRouter>);
    await userEvent.click(await screen.findByRole('button', { name: /start/i }));
    await userEvent.click(await screen.findByRole('button', { name: /keeping money/i }));
    await waitFor(() => expect(screen.getByText(/your best/i)).toBeInTheDocument());
  });

  it('has no axe violations on the start screen', async () => {
    const { container } = render(<MemoryRouter><QuizRush /></MemoryRouter>);
    await screen.findByRole('button', { name: /start/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
