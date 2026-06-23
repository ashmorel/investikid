import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import MoneyWord from '../MoneyWord';
import * as api from '@/api/moneyword';

vi.mock('@/api/moneyword');

const BASE_STATE = {
  length: 5,
  max_guesses: 6,
  guesses: [],
  completed: false,
  solved: false,
  definition: null,
  already_played: false,
};

beforeEach(() => {
  vi.mocked(api.getMoneyWordToday).mockResolvedValue({ ...BASE_STATE });
  vi.mocked(api.submitMoneyWordGuess).mockResolvedValue({
    ...BASE_STATE,
    guesses: [{ word: 'ASSET', feedback: ['correct', 'correct', 'correct', 'correct', 'correct'] }],
    completed: true,
    solved: true,
    definition: 'Something valuable owned by a person or company.',
  });
});

describe('MoneyWord', () => {
  it('renders initial board and submits a guess via on-screen keyboard', async () => {
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    // Wait for the puzzle to load (grid visible)
    await screen.findByRole('grid');

    // Tap letters A S S E T on the on-screen keyboard
    for (const letter of ['A', 'S', 'S', 'E', 'T']) {
      await userEvent.click(screen.getByRole('button', { name: new RegExp(`^${letter}$`, 'i') }));
    }

    // Press Enter
    await userEvent.click(screen.getByRole('button', { name: /enter/i }));

    // Definition should appear after solved
    await waitFor(() => expect(screen.getByText(/something valuable/i)).toBeInTheDocument());

    // Share button should appear
    expect(screen.getByRole('button', { name: /share/i })).toBeInTheDocument();
  });

  it('has no axe violations on the initial board', async () => {
    const { container } = render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByRole('grid');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows friendly message when puzzle fails to load', async () => {
    vi.mocked(api.getMoneyWordToday).mockResolvedValue(null);
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByText(/couldn't load/i);
  });

  it('shows completed state immediately when already_played', async () => {
    vi.mocked(api.getMoneyWordToday).mockResolvedValue({
      ...BASE_STATE,
      guesses: [{ word: 'ASSET', feedback: ['correct', 'correct', 'correct', 'correct', 'correct'] }],
      completed: true,
      solved: true,
      already_played: true,
      definition: 'Something valuable owned by a person or company.',
    });
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByText(/something valuable/i);
  });
});
