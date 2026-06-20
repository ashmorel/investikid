import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LessonDraftReview from '../LessonDraftReview';

const SAFE = {
  id: 's1',
  level_id: 'L1',
  type: 'card' as const,
  content_json: { title: 'T', body: 'B' },
  concept: 'c',
  moderation_safe: true,
  moderation_category: null,
  created_at: '2026-01-01',
};
const FLAGGED = {
  ...SAFE,
  id: 'f1',
  moderation_safe: false,
  moderation_category: 'violence',
};
const UK_RESIDUE = {
  ...SAFE,
  id: 'r1',
  adaptation_flags: { uk_residue: ['£', 'ISA'], suspect: true },
};

const approveMutate = vi.fn();
const updateMutate = vi.fn();
const regenerateMutate = vi.fn();
const rejectMutate = vi.fn();
const generateMutate = vi.fn();
const approveDraftsMutate = vi.fn();

// The published-lessons list backing useLevelLessons; mutate per-test so the
// "Publish & replace" button only appears when there are published lessons.
let publishedLessons: { id: string }[] = [{ id: 'pub1' }];

vi.mock('@/api/admin', () => ({
  useLevelDrafts: () => ({ data: [SAFE, FLAGGED, UK_RESIDUE], isLoading: false }),
  useLevelLessons: () => ({ data: publishedLessons }),
  useGenerateLevelLessons: () => ({ mutate: generateMutate, isPending: false }),
  useApproveDraft: () => ({ mutate: approveMutate, isPending: false }),
  useApproveDrafts: () => ({ mutate: approveDraftsMutate, isPending: false }),
  useUpdateDraft: () => ({ mutate: updateMutate, isPending: false }),
  useRegenerateDraft: () => ({ mutate: regenerateMutate, isPending: false }),
  useRejectDraft: () => ({ mutate: rejectMutate, isPending: false }),
}));

function renderReview() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <LessonDraftReview levelId="L1" />
    </QueryClientProvider>,
  );
}

describe('LessonDraftReview', () => {
  beforeEach(() => {
    approveMutate.mockClear();
    updateMutate.mockClear();
    regenerateMutate.mockClear();
    rejectMutate.mockClear();
    generateMutate.mockClear();
    approveDraftsMutate.mockClear();
    publishedLessons = [{ id: 'pub1' }];
  });

  it('flagged draft shows category and disables Approve; safe draft Approve enabled', () => {
    renderReview();
    const flaggedCard = screen.getByTestId('draft-f1');
    expect(within(flaggedCard).getByText(/flagged/i)).toBeInTheDocument();
    expect(within(flaggedCard).getByText(/violence/i)).toBeInTheDocument();
    expect(within(flaggedCard).getByRole('button', { name: /approve/i })).toBeDisabled();

    const safeCard = screen.getByTestId('draft-s1');
    expect(within(safeCard).getByRole('button', { name: /approve/i })).toBeEnabled();
  });

  it('clicking safe Approve calls approve mutate with the id', async () => {
    const user = userEvent.setup();
    renderReview();
    const safeCard = screen.getByTestId('draft-s1');
    await user.click(within(safeCard).getByRole('button', { name: /approve/i }));
    expect(approveMutate).toHaveBeenCalledWith('s1');
  });

  it('clicking safe Reject opens confirm dialog; confirming calls reject mutate', async () => {
    const user = userEvent.setup();
    renderReview();
    const safeCard = screen.getByTestId('draft-s1');
    await user.click(within(safeCard).getByRole('button', { name: /reject/i }));
    const dialog = screen.getByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /confirm/i }));
    expect(rejectMutate).toHaveBeenCalledWith('s1');
  });

  it('clicking Regenerate calls regenerate mutate with the id', async () => {
    const user = userEvent.setup();
    renderReview();
    const safeCard = screen.getByTestId('draft-s1');
    await user.click(within(safeCard).getByRole('button', { name: /regenerate/i }));
    expect(regenerateMutate).toHaveBeenCalledWith('s1');
  });

  it('draft with UK residue shows the adaptation badge; safe draft does not', () => {
    renderReview();
    const residueCard = screen.getByTestId('draft-r1');
    expect(within(residueCard).getByText(/may not be fully adapted/i)).toBeInTheDocument();
    expect(within(residueCard).getByText(/ISA/)).toBeInTheDocument();

    const safeCard = screen.getByTestId('draft-s1');
    expect(within(safeCard).queryByText(/may not be fully adapted/i)).not.toBeInTheDocument();
  });

  it('clicking Approve all calls approveDrafts mutate with false', async () => {
    const user = userEvent.setup();
    renderReview();
    await user.click(screen.getByRole('button', { name: /approve all/i }));
    expect(approveDraftsMutate).toHaveBeenCalledWith(false);
  });

  it('Publish & replace shows when published lessons exist; confirming calls mutate with true', async () => {
    const user = userEvent.setup();
    renderReview();
    await user.click(screen.getByRole('button', { name: /publish & replace/i }));
    const dialog = screen.getByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: /confirm/i }));
    expect(approveDraftsMutate).toHaveBeenCalledWith(true);
  });

  it('Publish & replace hidden with no published lessons; Approve all still shown', () => {
    publishedLessons = [];
    renderReview();
    expect(screen.queryByRole('button', { name: /publish & replace/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve all/i })).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderReview();
    expect(await axe(container)).toHaveNoViolations();
  });
});
