import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';

// ── Mock the diagnostic API module ───────────────────────────────────
vi.mock('@/api/diagnostic', () => ({
  startDiagnostic: vi.fn(),
  submitDiagnostic: vi.fn(),
  useEvidence: vi.fn(),
  useRecheckStatus: vi.fn(),
}));

// ── Mock useNavigate ─────────────────────────────────────────────────
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

// ── Mock useAgeTier ─────────────────────────────────────────────────
vi.mock('@/lib/ageTier', () => ({
  useAgeTier: vi.fn(() => 'explorer' as const),
  DEFAULT_TIER: 'explorer',
}));

import { useRecheckStatus, type RecheckStatus } from '@/api/diagnostic';
import ProgressCheckCard from '../ProgressCheckCard';

const mockUseRecheckStatus = useRecheckStatus as unknown as ReturnType<typeof vi.fn>;

function mockStatus(data: RecheckStatus | undefined, opts?: { isLoading?: boolean; isError?: boolean }) {
  mockUseRecheckStatus.mockReturnValue({
    data,
    isLoading: opts?.isLoading ?? false,
    isError: opts?.isError ?? false,
  } as unknown as UseQueryResult<RecheckStatus | null, Error>);
}

function renderCard() {
  return render(
    <MemoryRouter>
      <ProgressCheckCard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockNavigate.mockReset();
});

// ─────────────────────────────────────────────────────────────────────

describe('ProgressCheckCard — due:true', () => {
  beforeEach(() => {
    mockStatus({ due: true, milestone: 3, active_days: 14, completed_checks: 2 });
  });

  it('renders the card title and CTA when due is true', () => {
    renderCard();
    // Actual translated text from diagnostic.json
    expect(screen.getByText('Progress check')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /take the check/i })).toBeInTheDocument();
  });

  it('launch CTA navigates to the progress-check route', () => {
    renderCard();
    fireEvent.click(screen.getByRole('button', { name: /take the check/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/progress-check');
  });

  it('dismiss button hides the card for the session', () => {
    const { container } = renderCard();
    expect(container).not.toBeEmptyDOMElement();

    fireEvent.click(screen.getByRole('button', { name: /later/i }));
    expect(container).toBeEmptyDOMElement();
  });

  it('launch CTA and dismiss are at least 44px tall', () => {
    renderCard();
    const cta = screen.getByRole('button', { name: /take the check/i });
    const dismiss = screen.getByRole('button', { name: /later/i });
    for (const btn of [cta, dismiss]) {
      const cls = btn.getAttribute('class') ?? '';
      expect(cls).toMatch(/min-h-\[44px\]/);
    }
  });

  it('has no axe violations when due', async () => {
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });
});

// ─────────────────────────────────────────────────────────────────────

describe('ProgressCheckCard — hidden states', () => {
  it('renders nothing when due is false', () => {
    mockStatus({ due: false, milestone: null, active_days: 3, completed_checks: 0 });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing while loading', () => {
    mockStatus(undefined, { isLoading: true });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing on error', () => {
    mockStatus(undefined, { isError: true });
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when data is undefined (no due field)', () => {
    mockStatus(undefined);
    const { container } = renderCard();
    expect(container).toBeEmptyDOMElement();
  });
});
