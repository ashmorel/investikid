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

  it('share copies the grid and shows a visible confirmation (clipboard fallback)', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    // jsdom has no navigator.share, so this exercises the clipboard fallback.
    // Stub clipboard narrowly (don't replace navigator — that breaks userEvent).
    const prev = Object.getOwnPropertyDescriptor(window.navigator, 'clipboard');
    Object.defineProperty(window.navigator, 'clipboard', { value: { writeText }, configurable: true });

    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByRole('grid');
    for (const letter of ['A', 'S', 'S', 'E', 'T']) {
      await userEvent.click(screen.getByRole('button', { name: new RegExp(`^${letter}$`, 'i') }));
    }
    await userEvent.click(screen.getByRole('button', { name: /enter/i }));
    await waitFor(() => expect(screen.getByText(/something valuable/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /share/i }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const shared = writeText.mock.calls[0][0] as string;
    expect(shared).toContain('🟩🟩🟩🟩🟩');
    // Wordle-style label (date + score) and the app link for sharing.
    expect(shared).toMatch(/MoneyWord · .+ · 1\/\d+/);
    expect(shared).toContain('app.investikid.ai');
    // Visible confirmation (the old bug: copied silently, looked broken)
    expect(await screen.findByRole('status')).toHaveTextContent(/copied/i);

    if (prev) Object.defineProperty(window.navigator, 'clipboard', prev);
    else Reflect.deleteProperty(window.navigator, 'clipboard');
  });

  it('has no axe violations on the initial board', async () => {
    const { container } = render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByRole('grid');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows how-to-play instructions with the feedback legend', async () => {
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByRole('grid');
    expect(screen.getByText(/how to play/i)).toBeInTheDocument();
    expect(screen.getByText(/right letter, right spot/i)).toBeInTheDocument();
    expect(screen.getByText(/not in the word/i)).toBeInTheDocument();
  });

  it('shows friendly message when puzzle fails to load', async () => {
    vi.mocked(api.getMoneyWordToday).mockResolvedValue(null);
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByText(/couldn't load/i);
  });

  it('shows the error view (not an infinite spinner) when the request throws', async () => {
    // apiFetch THROWS on any non-2xx (e.g. 503 no_daily_word) — it never returns
    // null for an error. The load effect must catch it and fall into the error
    // view, not stay stuck on "Loading today's puzzle…" forever.
    vi.mocked(api.getMoneyWordToday).mockRejectedValue(new Error('503 no_daily_word'));
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByText(/couldn't load/i);
    expect(screen.queryByText(/loading today/i)).not.toBeInTheDocument();
  });

  it('recovers (no stuck spinner) when a guess submission throws', async () => {
    vi.mocked(api.submitMoneyWordGuess).mockRejectedValue(new Error('500'));
    render(<MemoryRouter><MoneyWord /></MemoryRouter>);
    await screen.findByRole('grid');
    for (const letter of ['A', 'S', 'S', 'E', 'T']) {
      await userEvent.click(screen.getByRole('button', { name: new RegExp(`^${letter}$`, 'i') }));
    }
    await userEvent.click(screen.getByRole('button', { name: /enter/i }));
    // The Enter button must become usable again (not stuck disabled/submitting).
    await waitFor(() => expect(screen.getByRole('button', { name: /enter/i })).toBeEnabled());
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
