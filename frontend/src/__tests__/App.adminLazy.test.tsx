import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App';

// Admin session so AdminLayout renders its tree instead of redirecting.
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({
    data: { id: 1, role: 'child', is_admin: true },
    isLoading: false,
  }),
}));

vi.mock('@/api/admin', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/admin')>();
  return {
    ...actual,
    useAdminStats: () => ({
      data: { modules: 2, lessons: 10, badges: 3, challenges: 1 },
      isLoading: false,
    }),
  };
});

describe('lazy /admin route', () => {
  it('renders the admin dashboard behind Suspense', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/admin']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    // findBy* waits for the lazy chunks to resolve through the Suspense boundary.
    expect(await screen.findByText('Dashboard')).toBeInTheDocument();
    expect(await screen.findByText('Content overview')).toBeInTheDocument();
  });
});
