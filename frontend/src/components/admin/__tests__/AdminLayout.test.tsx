import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import AdminLayout from '../AdminLayout';

// Stub out AdminSidebar so we don't need to boot the full admin tree
vi.mock('../AdminSidebar', () => ({ default: () => <nav data-testid="admin-sidebar" /> }));

vi.mock('@/hooks/useChildSession', () => ({ useChildSession: vi.fn() }));

import { useChildSession } from '@/hooks/useChildSession';
const mockUseChildSession = vi.mocked(useChildSession);

function wrap(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={ui}>
            <Route index element={<div data-testid="admin-child">Admin content</div>} />
          </Route>
          <Route path="/home" element={<div data-testid="home-page">Home</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AdminLayout', () => {
  it('shows loading state while session is loading', () => {
    mockUseChildSession.mockReturnValue({ data: undefined, isLoading: true } as ReturnType<typeof useChildSession>);
    wrap(<AdminLayout />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('redirects to /home when there is no session', () => {
    mockUseChildSession.mockReturnValue({ data: null, isLoading: false } as ReturnType<typeof useChildSession>);
    wrap(<AdminLayout />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('redirects to /home when session exists but is_admin is false', () => {
    mockUseChildSession.mockReturnValue({
      data: { id: '1', email: 'u@e.com', username: 'kid', dob: '', country_code: 'GB',
               currency_code: 'GBP', topic_path: null, is_premium: false, is_admin: false,
               parent_email: null, created_at: '', email_verified_at: null },
      isLoading: false,
    } as ReturnType<typeof useChildSession>);
    wrap(<AdminLayout />);
    expect(screen.getByTestId('home-page')).toBeInTheDocument();
  });

  it('renders sidebar and outlet when is_admin is true', () => {
    mockUseChildSession.mockReturnValue({
      data: { id: '1', email: 'u@e.com', username: 'admin', dob: '', country_code: 'GB',
               currency_code: 'GBP', topic_path: null, is_premium: false, is_admin: true,
               parent_email: null, created_at: '', email_verified_at: null },
      isLoading: false,
    } as ReturnType<typeof useChildSession>);
    wrap(<AdminLayout />);
    expect(screen.getByTestId('admin-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('admin-child')).toBeInTheDocument();
  });
});
