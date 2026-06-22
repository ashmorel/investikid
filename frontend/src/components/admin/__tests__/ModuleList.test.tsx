import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ModuleList from '../ModuleList';

const mockModules = [
  { id: '1', topic: 'stocks', title: 'Intro to Stocks', icon: '📈', is_premium: false, country_codes: [], market_code: 'GB', order_index: 0, lesson_count: 3, archived_at: null },
  { id: '2', topic: 'savings', title: 'US Saving', icon: '🏦', is_premium: true, country_codes: [], market_code: 'US', order_index: 0, lesson_count: 2, archived_at: null },
  { id: '3', topic: 'old', title: 'Retired Module', icon: '🗄️', is_premium: false, country_codes: [], market_code: 'GB', order_index: 2, lesson_count: 4, archived_at: new Date(Date.now() - 5 * 86_400_000).toISOString() },
];

const mockReorder = vi.fn();
const mockDelete = vi.fn();
const mockRestore = vi.fn();

vi.mock('@/api/admin', () => ({
  useModules: () => ({ data: mockModules, isLoading: false }),
  useReorderModules: () => ({ mutate: mockReorder }),
  useDeleteModule: () => ({ mutate: mockDelete }),
  useRestoreModule: () => ({ mutate: mockRestore, isPending: false }),
}));

vi.mock('@/api/market', () => ({
  marketApi: {
    list: () => Promise.resolve([
      { code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true },
      { code: 'US', name: 'United States', currency_code: 'USD', has_content: true },
    ]),
  },
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
    expect(screen.getByText('US Saving')).toBeInTheDocument();
  });

  it('shows a market badge on each module', () => {
    render(<ModuleList />, { wrapper });
    // GB on the active GB module, US on the active US module
    expect(screen.getAllByText('GB').length).toBeGreaterThan(0);
    expect(screen.getAllByText('US').length).toBeGreaterThan(0);
  });

  it('filters modules by the selected market tab', async () => {
    render(<ModuleList />, { wrapper });
    // Default "All" shows both markets' active modules
    expect(screen.getByText('Intro to Stocks')).toBeInTheDocument();
    expect(screen.getByText('US Saving')).toBeInTheDocument();
    // Click the US market tab (name resolves async from marketApi)
    fireEvent.click(await screen.findByRole('button', { name: /United States/ }));
    expect(screen.queryByText('Intro to Stocks')).not.toBeInTheDocument();
    expect(screen.getByText('US Saving')).toBeInTheDocument();
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

  it('shows archived modules in a separate section with a purge countdown', () => {
    render(<ModuleList />, { wrapper });
    const heading = screen.getByText('Archived');
    const section = heading.parentElement as HTMLElement;
    // Retired module is under Archived, not the active list…
    expect(within(section).getByText('Retired Module')).toBeInTheDocument();
    expect(within(section).getByText(/Auto-deletes in 25 days/)).toBeInTheDocument();
    // …and active modules are NOT inside the archived section.
    expect(within(section).queryByText('Intro to Stocks')).not.toBeInTheDocument();
  });

  it('restores an archived module', () => {
    render(<ModuleList />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /restore/i }));
    expect(mockRestore).toHaveBeenCalledWith('3');
  });
});
