import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleForm from '@/components/admin/ModuleForm';

vi.mock('@/api/admin', () => ({
  useModules: () => ({
    data: [
      { id: '1', topic: 'stocks', title: 'Prereq Mod', icon: '📈', is_premium: false, country_codes: [], order_index: 0, lesson_count: 2, prerequisite_ids: [], min_age: null, max_age: null },
    ],
    isLoading: false,
  }),
  useCreateModule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateModule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useLessons: () => ({ data: [], isLoading: false }),
  useCountries: () => ({ data: ['GB'], isLoading: false }),
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

describe('ModuleForm with prerequisites a11y', () => {
  it('passes axe audit', async () => {
    const { container } = render(<ModuleForm />, { wrapper });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
