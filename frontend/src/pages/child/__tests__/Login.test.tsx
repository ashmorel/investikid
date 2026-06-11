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

describe('Login demo entry', () => {
  it('shows a "Try a lesson first" link to /try', () => {
    render(wrap(<Login />));
    expect(screen.getByRole('link', { name: /try a lesson first/i })).toHaveAttribute('href', '/try');
  });
});
