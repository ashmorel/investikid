import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import ConceptsAdmin from '../ConceptsAdmin';

// ── Mock API hooks ────────────────────────────────────────────────────────────

const createMut = vi.fn().mockResolvedValue({});
const patchMut = vi.fn().mockResolvedValue({});

const mockGroups = [
  {
    topic: 'stocks',
    unmapped_count: 3,
    concepts: [
      {
        id: 'c1', topic: 'stocks', slug: 'stocks-basics', name: 'Stocks Basics',
        blurb: 'Intro', difficulty_tier: 1, order_index: 0, lesson_count: 5,
      },
      {
        id: 'c2', topic: 'stocks', slug: 'dividends', name: 'Dividends',
        blurb: null, difficulty_tier: 2, order_index: 1, lesson_count: 2,
      },
    ],
  },
  {
    topic: 'savings',
    unmapped_count: 0,
    concepts: [],
  },
];

vi.mock('@/api/adminConcepts', () => ({
  useConcepts: () => ({ data: mockGroups, isLoading: false }),
  useCreateConcept: () => ({ mutateAsync: createMut, isPending: false }),
  usePatchConcept: () => ({ mutateAsync: patchMut, isPending: false }),
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

describe('ConceptsAdmin', () => {
  beforeEach(() => {
    createMut.mockClear();
    patchMut.mockClear();
  });

  it('renders topic groups with concept rows', () => {
    render(<ConceptsAdmin />);
    // Topic headings rendered as <h3>
    expect(screen.getByRole('heading', { name: 'stocks' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'savings' })).toBeInTheDocument();
    // Concept names
    expect(screen.getByText('Stocks Basics')).toBeInTheDocument();
    expect(screen.getByText('Dividends')).toBeInTheDocument();
  });

  it('shows unmapped count badge for topics with unmapped lessons', () => {
    render(<ConceptsAdmin />);
    // stocks group has unmapped_count: 3
    expect(screen.getByText('concepts.unmappedBadge:3')).toBeInTheDocument();
  });

  it('does not show unmapped badge when count is 0', () => {
    render(<ConceptsAdmin />);
    // savings group has unmapped_count: 0 — badge should be absent
    const badges = screen.queryAllByText(/concepts\.unmappedBadge:0/);
    expect(badges).toHaveLength(0);
  });

  it('switches form to edit mode on Edit click', () => {
    render(<ConceptsAdmin />);
    const editButtons = screen.getAllByText('concepts.edit');
    fireEvent.click(editButtons[0]);
    expect(screen.getByDisplayValue('stocks-basics')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Stocks Basics')).toBeInTheDocument();
  });

  it('submitting the edit form calls the patch API', async () => {
    render(<ConceptsAdmin />);
    const editButtons = screen.getAllByText('concepts.edit');
    fireEvent.click(editButtons[0]);

    // Change name
    const nameInput = screen.getByDisplayValue('Stocks Basics');
    fireEvent.change(nameInput, { target: { value: 'Stocks Basics Updated' } });

    fireEvent.click(screen.getByText('concepts.save'));
    await waitFor(() => expect(patchMut).toHaveBeenCalledTimes(1));
    const call = patchMut.mock.calls[0][0] as { id: string; body: { name: string } };
    expect(call.id).toBe('c1');
    expect(call.body.name).toBe('Stocks Basics Updated');
  });

  it('submitting the create form calls the create API', async () => {
    render(<ConceptsAdmin />);
    // Fill the create form (starts empty, no edit selected)
    const slugInput = screen.getByPlaceholderText('e.g. stocks-what-is-a-share');
    fireEvent.change(slugInput, { target: { value: 'new-slug' } });

    // The name input is required and has no placeholder — find it by the label text key
    const nameInputs = screen.getAllByRole('textbox') as HTMLInputElement[];
    const nameInput = nameInputs.find((el) => el.required && el !== slugInput);
    if (nameInput) fireEvent.change(nameInput, { target: { value: 'New Concept' } });

    fireEvent.click(screen.getByText('concepts.save'));
    await waitFor(() => expect(createMut).toHaveBeenCalledTimes(1));
    const call = createMut.mock.calls[0][0] as { slug: string; name: string };
    expect(call.slug).toBe('new-slug');
  });

  it('has no axe accessibility violations (WCAG 2.2 AA)', async () => {
    const { container } = render(<ConceptsAdmin />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
