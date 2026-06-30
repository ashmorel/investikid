import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';

// ── Mock the API module before importing the page ─────────────────
vi.mock('@/api/diagnostic', () => ({
  startDiagnostic: vi.fn(),
  submitDiagnostic: vi.fn(),
  useEvidence: vi.fn(),
  useRecheckStatus: vi.fn(),
}));

// Mock useAgeTier so we get a deterministic tier in tests
vi.mock('@/lib/ageTier', () => ({
  useAgeTier: vi.fn(() => 'explorer' as const),
  DEFAULT_TIER: 'explorer',
}));

import { startDiagnostic, submitDiagnostic } from '@/api/diagnostic';
import OnboardingDiagnostic from '../OnboardingDiagnostic';

const mockStart = startDiagnostic as unknown as ReturnType<typeof vi.fn>;
const mockSubmit = submitDiagnostic as unknown as ReturnType<typeof vi.fn>;

const SESSION_ID = 'sess-abc';
const ITEMS = [
  {
    id: 'q1',
    topic: 'saving',
    difficulty_tier: 1,
    question: 'What is a savings account?',
    choices: ['A loan', 'A place to store money', 'A type of stock', 'Insurance'],
  },
  {
    id: 'q2',
    topic: 'investing',
    difficulty_tier: 2,
    question: 'What does diversification mean?',
    choices: ['Putting all money in one place', 'Spreading money across many investments', 'Borrowing money', 'Saving cash'],
  },
];

const SUBMIT_RESULT = {
  kind: 'baseline',
  overall_score: 0.5,
  topics: [
    { topic: 'saving', correct: 1, attempted: 1 },
    { topic: 'investing', correct: 0, attempted: 1 },
  ],
  session_count: 1,
};

function renderPage(onComplete = vi.fn()) {
  return render(
    <MemoryRouter>
      <OnboardingDiagnostic onComplete={onComplete} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSubmit.mockResolvedValue(SUBMIT_RESULT);
});

// ─────────────────────────────────────────────────────────────────

describe('OnboardingDiagnostic — items present', () => {
  beforeEach(() => {
    mockStart.mockResolvedValue({ session_id: SESSION_ID, items: ITEMS });
  });

  it('renders questions returned by startDiagnostic', async () => {
    renderPage();
    await screen.findByText('What is a savings account?');
    expect(screen.getByText('A place to store money')).toBeInTheDocument();
  });

  it('is accessible while showing the first question (axe)', async () => {
    const { container } = renderPage();
    await screen.findByText('What is a savings account?');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('answer choices are at least 44px tall (iOS touch target)', async () => {
    const { container } = renderPage();
    await screen.findByText('What is a savings account?');
    const optionButtons = container.querySelectorAll('[role="radio"]');
    expect(optionButtons.length).toBeGreaterThan(0);
    for (const btn of Array.from(optionButtons)) {
      const cls = btn.getAttribute('class') ?? '';
      // OptionCard uses p-3.5 which gives adequate height; we verify the class is present
      // as a proxy for the sizing (pixel computed sizes unavailable in jsdom)
      expect(cls).toMatch(/p-3\.5|p-4|py-3|py-4|min-h/);
    }
  });

  it('selecting an answer and finishing calls submitDiagnostic with the chosen map', async () => {
    const onComplete = vi.fn();
    renderPage(onComplete);

    // Q1: select the second choice (index 1)
    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));

    // Click Check answer
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }));

    // Q2: select the second choice (index 1)
    await screen.findByText('What does diversification mean?');
    fireEvent.click(screen.getByRole('radio', { name: /spreading money across many investments/i }));

    // Click Finish
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));

    await waitFor(() =>
      expect(mockSubmit).toHaveBeenCalledWith({
        session_id: SESSION_ID,
        answers: { q1: 1, q2: 1 },
      }),
    );
  });

  it('shows a results screen with a chip per topic after submitting', async () => {
    renderPage();
    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }));
    await screen.findByText('What does diversification mean?');
    fireEvent.click(screen.getByRole('radio', { name: /spreading money across many investments/i }));
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));

    // Results screen
    await screen.findByText(/here's what you already know/i);
    // One chip per topic in SUBMIT_RESULT.topics
    expect(screen.getByText(/saving/i)).toBeInTheDocument();
    expect(screen.getByText(/investing/i)).toBeInTheDocument();
  });

  it('results screen is accessible (axe)', async () => {
    const { container } = renderPage();
    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }));
    await screen.findByText('What does diversification mean?');
    fireEvent.click(screen.getByRole('radio', { name: /spreading money across many investments/i }));
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));
    await screen.findByText(/here's what you already know/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('results screen CTA calls onComplete', async () => {
    const onComplete = vi.fn();
    renderPage(onComplete);
    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }));
    await screen.findByText('What does diversification mean?');
    fireEvent.click(screen.getByRole('radio', { name: /spreading money across many investments/i }));
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));
    await screen.findByText(/here's what you already know/i);

    fireEvent.click(screen.getByRole('button', { name: /let's go/i }));
    expect(onComplete).toHaveBeenCalled();
  });

  it('skip calls submitDiagnostic with skipped:true and calls onComplete', async () => {
    const onComplete = vi.fn();
    renderPage(onComplete);
    await screen.findByText('What is a savings account?');

    fireEvent.click(screen.getByRole('button', { name: /skip for now/i }));

    await waitFor(() =>
      expect(mockSubmit).toHaveBeenCalledWith({ session_id: SESSION_ID, skipped: true }),
    );
    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });
});

// ─────────────────────────────────────────────────────────────────

describe('OnboardingDiagnostic — empty bank', () => {
  it('auto-submits with skipped:true and completes to home without showing a quiz', async () => {
    mockStart.mockResolvedValue({ session_id: SESSION_ID, items: [] });
    const onComplete = vi.fn();
    renderPage(onComplete);

    // Should NOT render any question
    await waitFor(() => expect(mockSubmit).toHaveBeenCalledWith({ session_id: SESSION_ID, skipped: true }));
    await waitFor(() => expect(onComplete).toHaveBeenCalled());
    expect(screen.queryByRole('radio')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────

describe('OnboardingDiagnostic — error paths (no lockout)', () => {
  it('startDiagnostic rejection still calls onComplete', async () => {
    mockStart.mockRejectedValue(new Error('network error'));
    const onComplete = vi.fn();
    renderPage(onComplete);
    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });

  it('submitDiagnostic rejection after answering still calls onComplete', async () => {
    mockStart.mockResolvedValue({ session_id: SESSION_ID, items: [ITEMS[0]] });
    mockSubmit.mockRejectedValue(new Error('server error'));
    const onComplete = vi.fn();
    renderPage(onComplete);

    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));

    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });

  it('submitDiagnostic rejection on skip still calls onComplete', async () => {
    mockStart.mockResolvedValue({ session_id: SESSION_ID, items: ITEMS });
    mockSubmit.mockRejectedValue(new Error('server error'));
    const onComplete = vi.fn();
    renderPage(onComplete);

    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('button', { name: /skip for now/i }));

    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });
});

// ─────────────────────────────────────────────────────────────────
// New: kind='progress' prop tests
// ─────────────────────────────────────────────────────────────────

describe('OnboardingDiagnostic — kind=progress', () => {
  beforeEach(() => {
    mockStart.mockResolvedValue({ session_id: SESSION_ID, items: ITEMS });
    mockSubmit.mockResolvedValue({ ...SUBMIT_RESULT, kind: 'progress' });
  });

  it('calls startDiagnostic with kind="progress" when kind prop is progress', async () => {
    render(
      <MemoryRouter>
        <OnboardingDiagnostic kind="progress" onComplete={vi.fn()} />
      </MemoryRouter>,
    );
    await screen.findByText('What is a savings account?');
    expect(mockStart).toHaveBeenCalledWith('progress');
  });

  it('shows the progress results copy (not the baseline copy) on completion', async () => {
    render(
      <MemoryRouter>
        <OnboardingDiagnostic kind="progress" onComplete={vi.fn()} />
      </MemoryRouter>,
    );
    await screen.findByText('What is a savings account?');
    fireEvent.click(screen.getByRole('radio', { name: /a place to store money/i }));
    fireEvent.click(screen.getByRole('button', { name: /check answer/i }));
    await screen.findByText('What does diversification mean?');
    fireEvent.click(screen.getByRole('radio', { name: /spreading money across many investments/i }));
    fireEvent.click(screen.getByRole('button', { name: /finish/i }));

    // Should show the "grown" copy (from diagnostic.json results.progress_heading_explorer)
    await screen.findByText(/how much you've grown/i);
    // Should NOT show the baseline "already know" copy
    expect(screen.queryByText(/what you already know/i)).toBeNull();
  });

  it('baseline (default kind) still calls startDiagnostic with no argument / "baseline"', async () => {
    render(
      <MemoryRouter>
        <OnboardingDiagnostic onComplete={vi.fn()} />
      </MemoryRouter>,
    );
    await screen.findByText('What is a savings account?');
    // Called with 'baseline' (or without kind — mock should be called once)
    expect(mockStart).toHaveBeenCalledWith('baseline');
  });
});
