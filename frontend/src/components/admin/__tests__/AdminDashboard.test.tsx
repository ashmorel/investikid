import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminDashboard from '../AdminDashboard';

vi.mock('@/api/admin', () => ({
  useAdminStats: () => ({
    data: { modules: 12, lessons: 49, badges: 5, challenges: 3 },
    isLoading: false,
  }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('AdminDashboard', () => {
  it('renders stat cards with counts', () => {
    render(<AdminDashboard />, { wrapper });
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('49')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders section headings', () => {
    render(<AdminDashboard />, { wrapper });
    expect(screen.getByText(/modules/i)).toBeInTheDocument();
    expect(screen.getByText(/badges/i)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<AdminDashboard />, { wrapper });
    expect(await axe(container)).toHaveNoViolations();
  });
});
