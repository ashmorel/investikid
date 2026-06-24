import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ArcadeWordBank from '../ArcadeWordBank';
import * as api from '@/api/arcadeWordsAdmin';

vi.mock('@/api/arcadeWordsAdmin');

const PENDING_WORD = {
  id: 'w1',
  word: 'BUDGET',
  definition: 'A plan for spending money',
  language: 'en',
  length: 6,
  status: 'pending',
  source: 'llm',
  created_at: '2026-06-23T00:00:00Z',
};

const APPROVED_WORD = {
  id: 'w2',
  word: 'INVEST',
  definition: 'Put money into something to earn more',
  language: 'en',
  length: 6,
  status: 'approved',
  source: 'llm',
  created_at: '2026-06-23T00:00:00Z',
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.useArcadeWords).mockReturnValue({
    data: [PENDING_WORD],
    isLoading: false,
  } as unknown as ReturnType<typeof api.useArcadeWords>);
  vi.mocked(api.suggestArcadeWords).mockResolvedValue({ created: 3, skipped: 2 });
  vi.mocked(api.approveArcadeWord).mockResolvedValue(APPROVED_WORD);
  vi.mocked(api.rejectArcadeWord).mockResolvedValue({ ...PENDING_WORD, status: 'rejected' });
});

describe('ArcadeWordBank', () => {
  it('renders the word list from useArcadeWords', () => {
    wrap(<ArcadeWordBank />);
    expect(screen.getByDisplayValue('BUDGET')).toBeInTheDocument();
    expect(screen.getByDisplayValue('A plan for spending money')).toBeInTheDocument();
  });

  it('renders approve and reject buttons for pending words', () => {
    wrap(<ArcadeWordBank />);
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('calls suggestArcadeWords when Suggest button is clicked', async () => {
    wrap(<ArcadeWordBank />);
    const suggestBtn = screen.getByRole('button', { name: /suggest/i });
    await userEvent.click(suggestBtn);
    expect(api.suggestArcadeWords).toHaveBeenCalledWith(10);
  });

  it('reports the created and skipped counts from the suggest result', async () => {
    // The endpoint returns { created, skipped } — the message must reflect
    // `created` (not data.length, which was always 0 → the "0 queued" bug).
    wrap(<ArcadeWordBank />);
    await userEvent.click(screen.getByRole('button', { name: /suggest/i }));
    // i18n mock interpolates real catalogs: "Queued 3 new word(s) for review."
    expect(await screen.findByText(/queued 3 new word/i)).toBeInTheDocument();
    expect(screen.getByText(/2 suggestion\(s\) were skipped/i)).toBeInTheDocument();
  });

  it('calls approveArcadeWord with no edits when word/def unchanged', async () => {
    wrap(<ArcadeWordBank />);
    const approveBtn = screen.getByRole('button', { name: /approve/i });
    await userEvent.click(approveBtn);
    expect(api.approveArcadeWord).toHaveBeenCalledWith('w1', {
      word: undefined,
      definition: undefined,
    });
  });

  it('calls approveArcadeWord with edits when word is changed', async () => {
    wrap(<ArcadeWordBank />);
    const wordInput = screen.getByDisplayValue('BUDGET');
    await userEvent.clear(wordInput);
    await userEvent.type(wordInput, 'SAVE');
    const approveBtn = screen.getByRole('button', { name: /approve/i });
    await userEvent.click(approveBtn);
    expect(api.approveArcadeWord).toHaveBeenCalledWith(
      'w1',
      expect.objectContaining({ word: 'SAVE' }),
    );
  });

  it('calls rejectArcadeWord when reject button is clicked', async () => {
    wrap(<ArcadeWordBank />);
    const rejectBtn = screen.getByRole('button', { name: /reject/i });
    await userEvent.click(rejectBtn);
    expect(api.rejectArcadeWord).toHaveBeenCalledWith('w1');
  });

  it('shows empty state when no words', () => {
    vi.mocked(api.useArcadeWords).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof api.useArcadeWords>);
    wrap(<ArcadeWordBank />);
    expect(screen.getByText(/no words with this status/i)).toBeInTheDocument();
  });

  it('shows a Reject action on an already-approved word (and no Approve)', () => {
    vi.mocked(api.useArcadeWords).mockReturnValue({
      data: [APPROVED_WORD],
      isLoading: false,
    } as unknown as ReturnType<typeof api.useArcadeWords>);
    wrap(<ArcadeWordBank />);
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).toBeNull();
  });

  it('rejects an already-approved word via rejectArcadeWord', async () => {
    vi.mocked(api.useArcadeWords).mockReturnValue({
      data: [APPROVED_WORD],
      isLoading: false,
    } as unknown as ReturnType<typeof api.useArcadeWords>);
    wrap(<ArcadeWordBank />);
    await userEvent.click(screen.getByRole('button', { name: /reject/i }));
    expect(api.rejectArcadeWord).toHaveBeenCalledWith('w2');
  });

  it('shows a Restore (approve) action on a rejected word', () => {
    vi.mocked(api.useArcadeWords).mockReturnValue({
      data: [{ ...APPROVED_WORD, id: 'w3', status: 'rejected' }],
      isLoading: false,
    } as unknown as ReturnType<typeof api.useArcadeWords>);
    wrap(<ArcadeWordBank />);
    expect(screen.getByRole('button', { name: /restore/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reject/i })).toBeNull();
  });

  it('shows status tabs (defaulting to the approved bank) and a count', () => {
    wrap(<ArcadeWordBank />);
    expect(screen.getByRole('tab', { name: /approved/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /pending/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /rejected/i })).toBeInTheDocument();
    expect(screen.getByText(/word\(s\) in this view/i)).toBeInTheDocument();
  });

  it('re-queries with the chosen status when a tab is clicked', async () => {
    wrap(<ArcadeWordBank />);
    await userEvent.click(screen.getByRole('tab', { name: /pending/i }));
    expect(api.useArcadeWords).toHaveBeenCalledWith('pending');
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<ArcadeWordBank />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
