import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Login from '../Login';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/login']}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Login parent link', () => {
  it('shows a "Manage your child" link to /parent/login', () => {
    render(wrap(<Login />));
    expect(screen.getByRole('link', { name: /manage your child/i })).toHaveAttribute('href', '/parent/login');
  });
});
