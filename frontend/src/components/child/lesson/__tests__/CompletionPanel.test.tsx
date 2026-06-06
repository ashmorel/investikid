import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompletionPanel } from '../CompletionPanel';

// Silence canvas-confetti in jsdom
vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

const BASE_RESULT = {
  xp_awarded: 25,
  already_completed: false,
  total_xp: 125,
  level: 2,
  streak_count: 3,
  streak_freezes: 0,
  practice_available: false,
};

function renderPanel(overrides = {}) {
  const onContinue = vi.fn();
  const result = { ...BASE_RESULT, ...overrides };
  render(
    <MemoryRouter>
      <CompletionPanel result={result} onContinue={onContinue} />
    </MemoryRouter>,
  );
  return { onContinue };
}

describe('CompletionPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders XP chip value', () => {
    renderPanel();
    expect(screen.getByText('+25')).toBeInTheDocument();
  });

  it('renders level chip value', () => {
    renderPanel();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders streak chip value', () => {
    renderPanel();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders "Lesson complete!" heading when not already completed', () => {
    renderPanel();
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Lesson complete!');
  });

  it('renders already-completed heading variant', () => {
    renderPanel({ already_completed: true });
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent("You've already done this one");
  });

  it('calls onContinue when Continue button is clicked', () => {
    const { onContinue } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    expect(onContinue).toHaveBeenCalledOnce();
  });
});
