import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

import AdminDashboard from '@/components/admin/AdminDashboard';
import OrderArrows from '@/components/admin/OrderArrows';
import ConfirmDialog from '@/components/admin/ConfirmDialog';

vi.mock('@/api/admin', () => ({
  useAdminStats: () => ({
    data: { modules: 12, lessons: 49, badges: 5, challenges: 3 },
    isLoading: false,
  }),
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('a11y: admin components', () => {
  it('AdminDashboard has no axe violations', async () => {
    const { container } = wrap(<AdminDashboard />);
    await waitFor(() => expect(screen.getByText(/Dashboard/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('OrderArrows has no axe violations', async () => {
    const mockOnMoveUp = vi.fn();
    const mockOnMoveDown = vi.fn();
    const { container } = wrap(<OrderArrows onMoveUp={mockOnMoveUp} onMoveDown={mockOnMoveDown} />);
    await waitFor(() => expect(screen.getByLabelText(/Move up/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ConfirmDialog (open) has no axe violations', async () => {
    const mockOnConfirm = vi.fn();
    const mockOnCancel = vi.fn();
    const { container } = wrap(
      <ConfirmDialog
        open
        title="Delete?"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    await waitFor(() => expect(screen.getByText(/Delete\?/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
