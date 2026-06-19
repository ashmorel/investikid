import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompletionPanel } from '../CompletionPanel';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

// Silence canvas-confetti in jsdom
vi.mock('canvas-confetti', () => ({ default: vi.fn() }));
vi.mock('@/lib/sound', () => ({ playSound: vi.fn() }));
vi.mock('@/lib/haptics', () => ({ haptic: vi.fn() }));

const BASE_RESULT = {
  xp_awarded: 25,
  already_completed: false,
  total_xp: 125,
  level: 2,
  streak_count: 3,
  streak_freezes: 0,
  practice_available: false,
  reward: { coins: 0, badge_name: null, badge_icon: null },
};

function renderPanel(overrides = {}) {
  const onContinue = vi.fn();
  const result = { ...BASE_RESULT, ...overrides };
  const view = render(
    <MemoryRouter>
      <CompletionPanel result={result} onContinue={onContinue} />
    </MemoryRouter>,
  );
  return { onContinue, result, ...view };
}

describe('CompletionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fires the lessonComplete sound and success haptic exactly once on mount', () => {
    const { rerender, result } = renderPanel();
    rerender(
      <MemoryRouter>
        <CompletionPanel result={result} onContinue={() => {}} />
      </MemoryRouter>,
    );
    expect(playSound).toHaveBeenCalledExactlyOnceWith('lessonComplete');
    expect(haptic).toHaveBeenCalledExactlyOnceWith('success');
  });

  it('does not fire celebration sound for an already-completed lesson', () => {
    renderPanel({ already_completed: true });
    expect(playSound).not.toHaveBeenCalled();
    expect(haptic).not.toHaveBeenCalled();
  });

  it('renders the XP count-up with the awarded value', async () => {
    renderPanel();
    // Screen-reader label carries the final value immediately.
    expect(screen.getByText('+25 XP')).toBeInTheDocument();
    // The animated figure settles on the final value.
    expect(await screen.findByText('+25', undefined, { timeout: 3000 })).toBeInTheDocument();
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
