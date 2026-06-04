import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RegionSwitcher } from '../RegionSwitcher';
import { authApi } from '@/api/auth';

vi.mock('@/api/auth', async (orig) => {
  const actual = await orig<typeof import('@/api/auth')>();
  return { ...actual, authApi: { ...actual.authApi, updatePreferences: vi.fn().mockResolvedValue({}) } };
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('RegionSwitcher', () => {
  it('renders three options with the current one marked', () => {
    wrap(<RegionSwitcher currentRegion="GB" />);
    const group = screen.getByRole('group', { name: /learning region/i });
    expect(within(group).getByRole('button', { name: /US/ })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /UK/ })).toHaveAttribute('aria-current', 'true');
    expect(within(group).getByRole('button', { name: /HK/ })).toBeInTheDocument();
  });

  it('calls updatePreferences with content_region on change', async () => {
    wrap(<RegionSwitcher currentRegion="US" />);
    await userEvent.click(screen.getByRole('button', { name: /HK/ }));
    expect(authApi.updatePreferences).toHaveBeenCalledWith({ content_region: 'HK' });
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<RegionSwitcher currentRegion="US" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
