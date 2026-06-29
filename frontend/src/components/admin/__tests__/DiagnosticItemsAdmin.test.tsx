import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import DiagnosticItemsAdmin from '../DiagnosticItemsAdmin';

// ── Mock API hooks ────────────────────────────────────────────────────────────

const generateMut = vi.fn().mockResolvedValue({ items: [] });
const patchMut = vi.fn().mockResolvedValue({});
const approveMut = vi.fn().mockResolvedValue({});
const rejectMut = vi.fn().mockResolvedValue({});
const retireMut = vi.fn().mockResolvedValue({});

const mockItems = [
  {
    id: 'item-1',
    market_code: 'GB',
    topic: 'stocks',
    concept_id: null,
    difficulty_tier: 1 as const,
    question: 'What is a share?',
    choices: ['A piece of cake', 'A unit of company ownership', 'A bank account', 'A type of bond'],
    answer_index: 1,
    explanation: 'A share represents partial ownership in a company.',
    status: 'draft' as const,
    source: 'generated',
    times_shown: 0,
    times_correct: 0,
    approved_by: null,
    approved_at: null,
    created_at: '2026-06-28T10:00:00Z',
  },
  {
    id: 'item-2',
    market_code: 'GB',
    topic: 'stocks',
    concept_id: 'c1',
    difficulty_tier: 2 as const,
    question: 'What does P/E ratio measure?',
    choices: ['Price per employee', 'Price-to-earnings ratio', 'Profit estimate', 'Portfolio equity'],
    answer_index: 1,
    explanation: 'P/E ratio compares a company\'s share price to earnings.',
    status: 'approved' as const,
    source: 'generated',
    times_shown: 10,
    times_correct: 7,
    approved_by: 'admin@example.com',
    approved_at: '2026-06-28T11:00:00Z',
    created_at: '2026-06-28T10:00:00Z',
  },
];

// Only stocks and savings have any coverage entries — the other 7 topics are completely absent from the array
const mockCoverage = [
  { topic: 'stocks', difficulty_tier: 1, approved_count: 0 },
  { topic: 'stocks', difficulty_tier: 2, approved_count: 3 },
  { topic: 'savings', difficulty_tier: 1, approved_count: 1 },
];

vi.mock('@/api/adminDiagnostic', () => ({
  useDiagnosticItems: () => ({ data: { items: mockItems, coverage: mockCoverage }, isLoading: false }),
  useGenerateItems: () => ({ mutateAsync: generateMut, isPending: false }),
  usePatchItem: () => ({ mutateAsync: patchMut, isPending: false }),
  useApproveItem: () => ({ mutateAsync: approveMut, isPending: false }),
  useRejectItem: () => ({ mutateAsync: rejectMut, isPending: false }),
  useRetireItem: () => ({ mutateAsync: retireMut, isPending: false }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => {
      if (o?.count !== undefined) return `${k}:${o.count}`;
      if (o?.name !== undefined) return `${k}:${o.name}`;
      return k;
    },
  }),
}));

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DiagnosticItemsAdmin', () => {
  beforeEach(() => {
    generateMut.mockClear();
    patchMut.mockClear();
    approveMut.mockClear();
    rejectMut.mockClear();
    retireMut.mockClear();
  });

  it('renders items with status chips', () => {
    render(<DiagnosticItemsAdmin />);
    expect(screen.getByText('What is a share?')).toBeInTheDocument();
    expect(screen.getByText('What does P/E ratio measure?')).toBeInTheDocument();
    // Status chips — draft and approved (may also appear in the filter select options)
    expect(screen.getAllByText('diagnosticItems.statusDraft').length).toBeGreaterThan(0);
    expect(screen.getAllByText('diagnosticItems.statusApproved').length).toBeGreaterThan(0);
  });

  it('highlights the correct answer distinctly from incorrect choices', () => {
    render(<DiagnosticItemsAdmin />);
    // The correct answer label '(correct)' key should appear for answer_index=1 choices
    const correctLabels = screen.getAllByText('diagnosticItems.correctChoice');
    expect(correctLabels.length).toBeGreaterThan(0);
    // The correct choice text is visible
    expect(screen.getByText('A unit of company ownership')).toBeInTheDocument();
  });

  it('generate control calls the generate API', async () => {
    render(<DiagnosticItemsAdmin />);
    const generateBtn = screen.getByText('diagnosticItems.generateButton');
    fireEvent.click(generateBtn);
    await waitFor(() => expect(generateMut).toHaveBeenCalledTimes(1));
    const call = generateMut.mock.calls[0][0] as {
      market_code: string;
      topic: string;
      difficulty_tier: number;
      count: number;
    };
    expect(call.topic).toBeTruthy();
    expect(call.count).toBeGreaterThan(0);
  });

  it('approve button calls approve mutation', async () => {
    render(<DiagnosticItemsAdmin />);
    // item-1 is draft → should have an approve button
    const approveBtns = screen.getAllByText('diagnosticItems.approve');
    fireEvent.click(approveBtns[0]);
    await waitFor(() => expect(approveMut).toHaveBeenCalledTimes(1));
    expect(approveMut.mock.calls[0][0]).toBe('item-1');
  });

  it('edit for draft item calls patch mutation', async () => {
    render(<DiagnosticItemsAdmin />);
    const editBtns = screen.getAllByText('diagnosticItems.edit');
    fireEvent.click(editBtns[0]);

    // Edit panel should appear
    await waitFor(() => expect(screen.getByText('diagnosticItems.editHeading')).toBeInTheDocument());

    // Change the question
    const questionInput = screen.getByDisplayValue('What is a share?');
    fireEvent.change(questionInput, { target: { value: 'What is a stock?' } });

    fireEvent.click(screen.getByText('diagnosticItems.save'));
    await waitFor(() => expect(patchMut).toHaveBeenCalledTimes(1));
    const call = patchMut.mock.calls[0][0] as { id: string; body: { question: string } };
    expect(call.id).toBe('item-1');
    expect(call.body.question).toBe('What is a stock?');
  });

  it('coverage summary shows under-covered (< 2) vs met (>= 2) cells', () => {
    render(<DiagnosticItemsAdmin />);
    // Coverage heading
    expect(screen.getByText('diagnosticItems.coverageHeading')).toBeInTheDocument();
    // 0 approved → coverageNone key (may appear multiple times for untracked topic/tier combos)
    expect(screen.getAllByText('diagnosticItems.coverageNone').length).toBeGreaterThan(0);
    // 3 approved → coverageMet:3
    expect(screen.getByText('diagnosticItems.coverageMet:3')).toBeInTheDocument();
    // 1 approved → coverageShort:1
    expect(screen.getByText('diagnosticItems.coverageShort:1')).toBeInTheDocument();
  });

  it('coverage table renders a 0-count cell for a topic absent from the coverage array', () => {
    render(<DiagnosticItemsAdmin />);
    // 'real_estate' has no entries in mockCoverage at all.
    // The full 9-topic grid must still include a row for it, showing coverageNone for all three tiers.
    // real_estate appears in select option(s) AND as a table cell — use getAllByText and find the <td>.
    const realEstateEls = screen.getAllByText('real_estate');
    const realEstateTd = realEstateEls.find((el) => el.tagName === 'TD');
    expect(realEstateTd).toBeInTheDocument();
    // All three tiers default to 0 → the row neighbours are coverageNone cells.
    // At least one coverageNone must exist for absent topics.
    const noneCells = screen.getAllByText('diagnosticItems.coverageNone');
    expect(noneCells.length).toBeGreaterThanOrEqual(1);
  });

  it('approve failure surfaces an error message scoped to the failing card only', async () => {
    approveMut.mockRejectedValueOnce(new Error('409 Conflict'));
    render(<DiagnosticItemsAdmin />);
    // item-1 is draft → has an approve button; item-2 is approved → no approve button
    const approveBtns = screen.getAllByText('diagnosticItems.approve');
    fireEvent.click(approveBtns[0]);
    // The error must appear exactly once (scoped to item-1's card only, not leaked to item-2)
    await waitFor(() =>
      expect(screen.getAllByText('diagnosticItems.actionError').length).toBe(1),
    );
    expect(screen.getAllByRole('alert').length).toBe(1);
  });

  it('"rejected" is not present as a status filter option', () => {
    render(<DiagnosticItemsAdmin />);
    // The status dropdown must NOT contain a 'rejected' option at all
    expect(screen.queryByText('diagnosticItems.statusRejected')).toBeNull();
  });

  it('has no axe accessibility violations (WCAG 2.2 AA)', async () => {
    const { container } = render(<DiagnosticItemsAdmin />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
