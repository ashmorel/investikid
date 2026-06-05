import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { TopNav } from '@/components/child/TopNav';

describe('TopNav', () => {
  it('renders Home, Lessons, Simulator, and Stats as links', () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <TopNav username="kid42" />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/home');
    expect(screen.getByRole('link', { name: 'Learn' })).toHaveAttribute('href', '/lessons');
    expect(screen.getByRole('link', { name: 'Simulator' })).toHaveAttribute('href', '/simulator');
    expect(screen.getByRole('link', { name: 'Stats' })).toHaveAttribute('href', '/stats');
  });
});
