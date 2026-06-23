import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';

// Mock the hook directly so no real QueryClient is needed
vi.mock('@/api/moneyword', () => ({
  useMoneyWordToday: vi.fn(),
}));

import { useMoneyWordToday } from '@/api/moneyword';
import ArcadeDailyCard from '../ArcadeDailyCard';

const mockUseMoneyWordToday = vi.mocked(useMoneyWordToday);

function renderCard() {
  return render(<MemoryRouter><ArcadeDailyCard /></MemoryRouter>);
}

describe('ArcadeDailyCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function mockData(data: unknown) {
    mockUseMoneyWordToday.mockReturnValue({ data } as unknown as ReturnType<typeof useMoneyWordToday>);
  }

  it('shows Play state when not started and links to /arcade/moneyword', async () => {
    mockData({ length: 5, max_guesses: 6, guesses: [], completed: false, solved: false, definition: null, already_played: false });

    const { container } = renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/arcade/moneyword');
    expect(link).toHaveAccessibleName(/play/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows Continue state with guess count when in progress', async () => {
    mockData({
      length: 5,
      max_guesses: 6,
      guesses: [
        { word: 'MONEY', feedback: ['absent', 'absent', 'absent', 'absent', 'absent'] },
        { word: 'STOCK', feedback: ['absent', 'absent', 'absent', 'absent', 'absent'] },
        { word: 'TRADE', feedback: ['absent', 'absent', 'absent', 'absent', 'absent'] },
      ],
      completed: false,
      solved: false,
      definition: null,
      already_played: false,
    });

    const { container } = renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/arcade/moneyword');
    expect(link).toHaveAccessibleName(/continue/i);
    expect(screen.getByText(/3 \/ 6/)).toBeTruthy();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('shows Done state when completed', async () => {
    mockData({
      length: 5,
      max_guesses: 6,
      guesses: [{ word: 'BONDS', feedback: ['correct', 'correct', 'correct', 'correct', 'correct'] }],
      completed: true,
      solved: true,
      definition: 'A fixed income instrument.',
      already_played: true,
    });

    const { container } = renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/arcade/moneyword');
    expect(link).toHaveAccessibleName(/done/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('degrades to Play state when data is null (failed fetch)', async () => {
    mockData(undefined);

    const { container } = renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/arcade/moneyword');
    expect(link).toHaveAccessibleName(/play/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
