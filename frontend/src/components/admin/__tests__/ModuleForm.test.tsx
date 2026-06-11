import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleForm from '../ModuleForm';

const { mockCreate, mockUpdate, mockParams } = vi.hoisted(() => ({
  mockCreate: vi.fn().mockResolvedValue({}),
  mockUpdate: vi.fn().mockResolvedValue({}),
  mockParams: { value: {} as Record<string, string | undefined> },
}));

vi.mock('@/api/admin', () => ({
  useModules: () => ({
    data: [
      {
        id: '1', topic: 'stocks', title: 'Intro to Stocks', icon: '📈', is_premium: false,
        country_codes: [], order_index: 0, lesson_count: 2, prerequisite_ids: [],
        min_age: null, max_age: null,
        standards_alignment: [
          { framework: 'UK MaPS/YE Financial Education Planning Framework', code: 'F1', label: 'Where money comes from' },
        ],
        sources: [
          { title: 'MaPS Framework', url: 'https://example.com/maps' },
        ],
      },
    ],
    isLoading: false,
  }),
  useCreateModule: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateModule: () => ({ mutateAsync: mockUpdate, isPending: false }),
  useLessons: () => ({ data: [], isLoading: false }),
  useCountries: () => ({ data: ['GB', 'US'], isLoading: false }),
  useCreateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteLesson: () => ({ mutate: vi.fn() }),
  useReorderLessons: () => ({ mutate: vi.fn() }),
  useModuleEngagement: () => ({ data: undefined, isLoading: true, isError: false }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => mockParams.value, useNavigate: () => vi.fn() };
});

beforeEach(() => {
  mockParams.value = {};
  mockCreate.mockClear();
  mockUpdate.mockClear();
});

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ModuleForm', () => {
  it('renders form fields for create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByLabelText(/topic/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/icon/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/premium/i)).toBeInTheDocument();
  });

  it('renders save button', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });

  it('renders prerequisite multi-select in create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByText(/prerequisites/i)).toBeInTheDocument();
  });

  it('renders age range inputs in create mode', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByLabelText(/min age/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max age/i)).toBeInTheDocument();
  });

  it('renders a completion cash reward input', () => {
    render(<ModuleForm />, { wrapper });
    expect(screen.getByLabelText(/completion cash reward/i)).toBeInTheDocument();
  });

  it('renders existing standards and sources values in edit mode', () => {
    mockParams.value = { moduleId: '1' };
    render(<ModuleForm />, { wrapper });
    expect(screen.getByDisplayValue('UK MaPS/YE Financial Education Planning Framework')).toBeInTheDocument();
    expect(screen.getByDisplayValue('F1')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Where money comes from')).toBeInTheDocument();
    expect(screen.getByDisplayValue('MaPS Framework')).toBeInTheDocument();
    expect(screen.getByDisplayValue('https://example.com/maps')).toBeInTheDocument();
  });

  it('adds and edits standards/sources rows and includes them in the save payload', async () => {
    const user = userEvent.setup();
    mockParams.value = { moduleId: '1' };
    render(<ModuleForm />, { wrapper });

    await user.click(screen.getByRole('button', { name: /add standard/i }));
    await user.type(screen.getByLabelText(/standard 2 framework/i), 'US National Standards for Personal Financial Education (CEE/Jump$tart 2021)');
    await user.type(screen.getByLabelText(/standard 2 code/i), 'I-4a');
    await user.type(screen.getByLabelText(/standard 2 label/i), 'Investing basics');

    await user.click(screen.getByRole('button', { name: /add source/i }));
    await user.type(screen.getByLabelText(/source 2 title/i), 'Jump$tart Standards');
    await user.type(screen.getByLabelText(/source 2 url/i), 'https://example.com/jumpstart');

    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => expect(mockUpdate).toHaveBeenCalled());
    const payload = mockUpdate.mock.calls[0][0];
    expect(payload.standards_alignment).toEqual([
      { framework: 'UK MaPS/YE Financial Education Planning Framework', code: 'F1', label: 'Where money comes from' },
      { framework: 'US National Standards for Personal Financial Education (CEE/Jump$tart 2021)', code: 'I-4a', label: 'Investing basics' },
    ]);
    expect(payload.sources).toEqual([
      { title: 'MaPS Framework', url: 'https://example.com/maps' },
      { title: 'Jump$tart Standards', url: 'https://example.com/jumpstart' },
    ]);
  });

  it('removes a standards row and sends null when no rows remain', async () => {
    const user = userEvent.setup();
    mockParams.value = { moduleId: '1' };
    render(<ModuleForm />, { wrapper });

    await user.click(screen.getByRole('button', { name: /remove standard 1/i }));
    expect(screen.queryByDisplayValue('F1')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^save$/i }));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalled());
    expect(mockUpdate.mock.calls[0][0].standards_alignment).toBeNull();
  });
});
