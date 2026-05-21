import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleList from '../ModuleList';

const mockModules = [
  { id: '1', topic: 'stocks', title: 'Intro to Stocks', icon: '📈', is_premium: false, country_codes: [], order_index: 0, lesson_count: 3 },
  { id: '2', topic: 'savings', title: 'Compound Interest', icon: '🏦', is_premium: true, country_codes: ['GB'], order_index: 1, lesson_count: 2 },
];

const mockReorder = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/admin', () => ({
  useModules: () => ({ data: mockModules, isLoading: false }),
  useReorderModules: () => ({ mutate: mockReorder }),
  useDeleteModule: () => ({ mutate: mockDelete }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ModuleList', () => {
  it('renders module titles', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText('Intro to Stocks')).toBeInTheDocument();
    expect(screen.getByText('Compound Interest')).toBeInTheDocument();
  });

  it('shows premium badge for premium modules', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
  });

  it('shows lesson count', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByText(/3 lessons/i)).toBeInTheDocument();
  });

  it('renders new module button', () => {
    render(<ModuleList />, { wrapper });
    expect(screen.getByRole('link', { name: /new module/i })).toBeInTheDocument();
  });
});
