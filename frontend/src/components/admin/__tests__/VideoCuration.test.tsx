import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import VideoCuration from '../VideoCuration';
import * as api from '@/api/videoCuration';

vi.mock('@/api/videoCuration');

vi.mock('@/api/admin', () => ({
  useModules: () => ({
    data: [
      { id: 'm1', title: 'Saving basics', topic: 'saving', market_code: 'GB' },
      // Archived module in the SAME market — must never be offered as an approve
      // or suggest target (an approved video would land in an invisible module).
      {
        id: 'm-arch',
        title: 'Archived Stock',
        topic: 'stocks',
        market_code: 'GB',
        archived_at: '2026-01-01T00:00:00Z',
      },
    ],
    isLoading: false,
  }),
  useLevels: () => ({
    data: [
      { id: 'l1', title: 'Level 1', module_id: 'm1' },
    ],
    isLoading: false,
  }),
}));

vi.mock('@/api/market', () => ({
  marketApi: {
    list: () => Promise.resolve([
      { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: false, is_selected: false, locked: false },
    ]),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.suggestVideos).mockResolvedValue({ created: 2 });
  vi.mocked(api.listVideoCandidates).mockResolvedValue([
    {
      id: '1',
      youtube_id: 'vid1',
      title: 'Saving 101',
      source: 'recovered',
      market_code: 'GB',
      suggested_module_id: 'm1',
      suggested_level_id: 'l1',
      embeddable: true,
      health_detail: null,
      status: 'pending',
      origin_context: 'saving / Old',
      thumbnail_url: null,
    },
  ]);
});

describe('VideoCuration', () => {
  it('renders pending candidates with an approve action', async () => {
    wrap(<VideoCuration />);
    expect(await screen.findByText('Saving 101')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
  });

  it('renders a module select for the candidate row', async () => {
    wrap(<VideoCuration />);
    await screen.findByText('Saving 101');
    // Both the suggest-panel module select AND the per-row module select must render.
    expect(screen.getAllByRole('combobox', { name: /module/i }).length).toBeGreaterThanOrEqual(2);
  });

  it('never offers archived modules as approve/suggest targets', async () => {
    wrap(<VideoCuration />);
    await screen.findByText('Saving 101');
    // Archived module is in the same market as the candidate but must be hidden
    // from BOTH the suggest panel and the per-row approve picker — otherwise an
    // approved video lands in a module no child can see.
    expect(screen.queryByRole('option', { name: 'Archived Stock' })).not.toBeInTheDocument();
    // The live, same-market module is still offered (in both selects).
    expect(screen.getAllByRole('option', { name: 'Saving basics' }).length).toBeGreaterThanOrEqual(2);
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<VideoCuration />);
    await screen.findByText('Saving 101');
    // axe-core cannot communicate with live <iframe> elements in jsdom; skip them.
    expect(await axe(container, { iframes: false })).toHaveNoViolations();
  });

  it('calls suggest then refetches', async () => {
    vi.mocked(api.suggestVideos).mockResolvedValue({ created: 2 });
    wrap(<VideoCuration />);
    await screen.findByText('Saving 101');

    // Select a module in the suggest panel (using the suggest-module select)
    const moduleSelect = screen.getByLabelText('Module for video suggestions');
    await userEvent.selectOptions(moduleSelect, 'm1');

    // Select a level
    const levelSelect = screen.getByLabelText('Level for video suggestions');
    await userEvent.selectOptions(levelSelect, 'l1');

    // Click the suggest button
    const suggestBtn = screen.getByRole('button', { name: /suggest videos/i });
    await userEvent.click(suggestBtn);

    expect(api.suggestVideos).toHaveBeenCalledWith({ module_id: 'm1', level_id: 'l1' });
  });
});
