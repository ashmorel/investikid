import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvestingTips } from '../InvestingTips';

vi.mock('@/api/simulator', () => ({
  simulatorApi: {
    getInvestingTips: vi.fn(),
    getStockHistory: vi.fn(() => Promise.resolve(null)),
  },
}));

import { simulatorApi } from '@/api/simulator';

const TIPS = [
  { id: 't1', title: 'Tip One', description: 'First tip body', example_ticker: 'AAPL', example_exchange: 'NASDAQ' },
  { id: 't2', title: 'Tip Two', description: 'Second tip body', example_ticker: 'MSFT', example_exchange: 'NASDAQ' },
  { id: 't3', title: 'Tip Three', description: 'Third tip body', example_ticker: 'F', example_exchange: 'NYSE' },
];

function setReducedMotion(reduce: boolean) {
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: q.includes('prefers-reduced-motion') ? reduce : false,
    media: q,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

async function renderTips() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <InvestingTips />
    </QueryClientProvider>,
  );
  // Tips load (the carousel renders once data resolves)
  await screen.findByText('Tip One');
  return utils;
}

beforeEach(() => {
  vi.mocked(simulatorApi.getInvestingTips).mockResolvedValue(TIPS as never);
  vi.mocked(simulatorApi.getStockHistory).mockResolvedValue(null as never);
  setReducedMotion(false);
  // jsdom has no scrollTo
  Element.prototype.scrollTo = vi.fn() as unknown as typeof Element.prototype.scrollTo;
  // shouldAdvanceTime keeps findBy/userEvent working while we control the interval
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function activeDotLabel(): string | null {
  const dots = screen.getAllByRole('button', { name: /go to tip/i });
  const active = dots.find((d) => d.getAttribute('aria-current') === 'true');
  return active ? active.getAttribute('aria-label') : null;
}

describe('InvestingTips auto-rotation', () => {
  it('auto-advances through tips and loops back to the first', async () => {
    await renderTips();
    expect(activeDotLabel()).toBe('Go to tip 1');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 3');
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // looped
  });

  it('pause halts advancing; play resumes', async () => {
    await renderTips();
    await userEvent.click(screen.getByRole('button', { name: /pause tips/i }));
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // still
    await userEvent.click(screen.getByRole('button', { name: /play tips/i }));
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
  });

  it('pauses while the tips region is hovered, resumes on leave', async () => {
    await renderTips();
    const region = screen.getByRole('group', { name: /investing tips/i });
    fireEvent.mouseEnter(region);
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // paused by hover
    fireEvent.mouseLeave(region);
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 2');
  });

  it('under prefers-reduced-motion: no auto-advance and no play/pause control', async () => {
    setReducedMotion(true);
    await renderTips();
    expect(screen.queryByRole('button', { name: /pause tips|play tips/i })).toBeNull();
    act(() => vi.advanceTimersByTime(7000));
    expect(activeDotLabel()).toBe('Go to tip 1'); // never advanced
  });

  it('tapping a dot jumps to that tip', async () => {
    await renderTips();
    await userEvent.click(screen.getByRole('button', { name: 'Go to tip 3' }));
    expect(activeDotLabel()).toBe('Go to tip 3');
    expect(Element.prototype.scrollTo).toHaveBeenCalled();
  });

  it('has no axe violations', async () => {
    const { container } = await renderTips();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('is collapsible and open by default; collapsing hides the tips', async () => {
    await renderTips();
    const toggle = screen.getByRole('button', { name: /^investing tips$/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Tip One')).toBeInTheDocument();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Tip One')).toBeNull();
  });
});
