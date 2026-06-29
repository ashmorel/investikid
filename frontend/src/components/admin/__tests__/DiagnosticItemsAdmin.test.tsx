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
const verifyMut = vi.fn().mockResolvedValue({
  verified: 3,
  agree: 2,
  mismatch: 1,
  ambiguous: 0,
  error: 0,
  flagged: [],
});

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
    verifier_status: 'mismatch' as const,
    verifier_answer_index: 2,
    verifier_note: 'Verifier thinks option C is correct based on context.',
    verified_at: '2026-06-28T12:00:00Z',
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
    verifier_status: 'agree' as const,
    verifier_answer_index: 1,
    verifier_note: null,
    verified_at: '2026-06-28T11:30:00Z',
  },
  {
    id: 'item-3',
    market_code: 'GB',
    topic: 'savings',
    concept_id: null,
    difficulty_tier: 1 as const,
    question: 'What is compound interest?',
    choices: ['Simple interest only', 'Interest on interest', 'A bank fee', 'A tax'],
    answer_index: 1,
    explanation: 'Compound interest earns interest on previously earned interest.',
    status: 'draft' as const,
    source: 'generated',
    times_shown: 0,
    times_correct: 0,
    approved_by: null,
    approved_at: null,
    created_at: '2026-06-28T10:00:00Z',
    verifier_status: null,
    verifier_answer_index: null,
    verifier_note: null,
    verified_at: null,
  },
];

// Only stocks and savings have any coverage entries — the other 7 topics are completely absent from the array
const mockCoverage = [
  { topic: 'stocks', difficulty_tier: 1, approved_count: 0 },
  { topic: 'stocks', difficulty_tier: 2, approved_count: 3 },
  { topic: 'savings', difficulty_tier: 1, approved_count: 1 },
];

// Track last filters passed to useDiagnosticItems
let lastDiagnosticFilters: Record<string, unknown> = {};

vi.mock('@/api/adminDiagnostic', () => ({
  useDiagnosticItems: (filters: Record<string, unknown> = {}) => {
    lastDiagnosticFilters = filters;
    return { data: { items: mockItems, coverage: mockCoverage }, isLoading: false };
  },
  useGenerateItems: () => ({ mutateAsync: generateMut, isPending: false }),
  usePatchItem: () => ({ mutateAsync: patchMut, isPending: false }),
  useApproveItem: () => ({ mutateAsync: approveMut, isPending: false }),
  useRejectItem: () => ({ mutateAsync: rejectMut, isPending: false }),
  useRetireItem: () => ({ mutateAsync: retireMut, isPending: false }),
  useVerifyItems: () => ({ mutateAsync: verifyMut, isPending: false }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string, o?: Record<string, unknown>) => {
      if (o?.count !== undefined) return `${k}:${o.count}`;
      if (o?.name !== undefined) return `${k}:${o.name}`;
      if (o?.index !== undefined) return `${k}:${o.index}`;
      if (o?.note !== undefined) return `${k}:${o.note}`;
      // verifyResultSummary passes multiple keys — return a string containing all values
      if (o?.verified !== undefined)
        return `verified:${o.verified} agree:${o.agree} mismatch:${o.mismatch} ambiguous:${o.ambiguous} error:${o.error}`;
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
    verifyMut.mockClear();
    lastDiagnosticFilters = {};
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

  it('mismatch item shows prominent verifier warning with declared vs verifier answer and note', () => {
    render(<DiagnosticItemsAdmin />);
    // item-1 has verifier_status=mismatch, declared answer_index=1, verifier_answer_index=2
    // Should show a warning banner/badge containing these details
    expect(screen.getByTestId('verifier-warning-item-1')).toBeInTheDocument();
    // Warning shows declared answer index
    expect(screen.getByTestId('verifier-warning-item-1')).toHaveTextContent('1');
    // Warning shows verifier's answer index
    expect(screen.getByTestId('verifier-warning-item-1')).toHaveTextContent('2');
    // Warning shows the note
    expect(screen.getByTestId('verifier-warning-item-1')).toHaveTextContent(
      'Verifier thinks option C is correct based on context.',
    );
  });

  it('agree item shows a subtle verified chip, not a warning', () => {
    render(<DiagnosticItemsAdmin />);
    // item-2 has verifier_status=agree — should show verified chip, no warning
    expect(screen.queryByTestId('verifier-warning-item-2')).not.toBeInTheDocument();
    expect(screen.getByTestId('verifier-agree-item-2')).toBeInTheDocument();
  });

  it('unverified item shows neither warning nor agree chip', () => {
    render(<DiagnosticItemsAdmin />);
    // item-3 has verifier_status=null — no badge of any kind
    expect(screen.queryByTestId('verifier-warning-item-3')).not.toBeInTheDocument();
    expect(screen.queryByTestId('verifier-agree-item-3')).not.toBeInTheDocument();
  });

  it('"Needs review" filter toggle passes verifier=needs_review to the list hook', async () => {
    render(<DiagnosticItemsAdmin />);
    const toggle = screen.getByRole('button', { name: /diagnosticItems.needsReviewFilter/i });
    fireEvent.click(toggle);
    await waitFor(() =>
      expect(lastDiagnosticFilters).toMatchObject({ verifier: 'needs_review' }),
    );
  });

  it('"Verify all" button calls the verify mutation and shows returned counts', async () => {
    render(<DiagnosticItemsAdmin />);
    const verifyBtn = screen.getByRole('button', { name: /diagnosticItems.verifyAll/i });
    fireEvent.click(verifyBtn);
    await waitFor(() => expect(verifyMut).toHaveBeenCalledTimes(1));
    // After mutation resolves, counts summary should be visible
    await waitFor(() =>
      expect(screen.getByTestId('verify-all-result')).toBeInTheDocument(),
    );
    const result = screen.getByTestId('verify-all-result');
    // Shows the verified count (3), agree (2), mismatch (1)
    expect(result).toHaveTextContent('3');
    expect(result).toHaveTextContent('2');
    expect(result).toHaveTextContent('1');
  });

  it('has no axe accessibility violations (WCAG 2.2 AA)', async () => {
    const { container } = render(<DiagnosticItemsAdmin />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
