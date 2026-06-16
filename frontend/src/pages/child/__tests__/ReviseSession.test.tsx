import { it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import ReviseSession from '../ReviseSession';

const session = {
  items: [
    { ref: 'r1', kind: 'weak', module_id: 'm', lesson_id: 'l', concept: 'Stocks?',
      question: 'What is a stock?', choices: ['A loan', 'A slice of a company'] },
  ],
};
vi.mock('@/api/revise', () => ({
  reviseApi: {
    getSession: vi.fn(() => Promise.resolve(session)),
    postAnswer: vi.fn(() => Promise.resolve({
      correct: true, answer_index: 1, explanation: 'A tiny piece.',
      xp_awarded: 5, goal_met: false,
    })),
  },
}));
import { reviseApi } from '@/api/revise';

function renderPage() {
  return render(<MemoryRouter initialEntries={['/revise/session']}><ReviseSession /></MemoryRouter>);
}

it('shows a weak badge, records an answer, then a summary', async () => {
  const { container } = renderPage();
  await screen.findByText('What is a stock?');
  expect(screen.getByText(/needs practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();

  fireEvent.click(screen.getByRole('button', { name: 'A slice of a company' }));
  await waitFor(() => expect(reviseApi.postAnswer).toHaveBeenCalledWith('r1', 1));
  await screen.findByText(/A tiny piece\./i); // explanation shown

  fireEvent.click(screen.getByRole('button', { name: /next|finish|done/i }));
  await screen.findByText(/1 \/ 1 correct/i); // summary
});

it('shows an empty state when nothing is due', async () => {
  (reviseApi.getSession as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ items: [] });
  renderPage();
  await screen.findByText(/nothing to revise right now/i);
});
