import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleForm from '../ModuleForm';

const mockCreate = vi.fn();
const mockUpdate = vi.fn();

vi.mock('@/api/admin', () => ({
  useModules: () => ({ data: [], isLoading: false }),
  useCreateModule: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateModule: () => ({ mutateAsync: mockUpdate, isPending: false }),
  useLessons: () => ({ data: [], isLoading: false }),
  useCountries: () => ({ data: ['GB', 'US'], isLoading: false }),
  useCreateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteLesson: () => ({ mutate: vi.fn() }),
  useReorderLessons: () => ({ mutate: vi.fn() }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({}), useNavigate: () => vi.fn() };
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
});
