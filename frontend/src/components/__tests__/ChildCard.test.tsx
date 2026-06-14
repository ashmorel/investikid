import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChildCard } from '../ChildCard';
import { parentApi, type Child } from '@/api/parent';

const BASE_CHILD: Child = {
  user_id: 'child-1',
  username: 'alex',
  country_code: 'GB',
  is_active: true,
  is_premium: false,
  parent_consent_given_at: '2026-05-01T10:00:00Z',
  consent_declined_at: null,
  deleted_at: null,
  deletion_requested_at: null,
  age_tier: 'explorer',
  tier_override: null,
  analytics: null,
};

function renderCard(child: Child = BASE_CHILD) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['children'], [child]);
  return render(
    <QueryClientProvider client={qc}>
      <ChildCard child={child} />
    </QueryClientProvider>,
  );
}

describe('ChildCard premium status (read-only)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows a Premium badge for a premium child (read-only, no switch)', () => {
    renderCard({ ...BASE_CHILD, is_premium: true });
    expect(screen.getByText(/Premium ✨/)).toBeInTheDocument();
    expect(screen.queryByRole('switch', { name: /premium/i })).toBeNull();
  });

  it('shows Free status for a non-premium child', () => {
    renderCard({ ...BASE_CHILD, is_premium: false });
    expect(screen.getByText(/Free plan/i)).toBeInTheDocument();
  });
});

describe('ChildCard experience mode', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows Auto when no override and the effective mode line', () => {
    renderCard();
    const select = screen.getByLabelText('Experience mode') as HTMLSelectElement;
    expect(select.value).toBe('auto');
    expect(screen.getByText(/Currently: Explorer/)).toBeInTheDocument();
  });

  it('shows the override value and effective Investor mode when overridden', () => {
    renderCard({ ...BASE_CHILD, tier_override: 'investor', age_tier: 'investor' });
    const select = screen.getByLabelText('Experience mode') as HTMLSelectElement;
    expect(select.value).toBe('investor');
    expect(screen.getByText(/Currently: Investor/)).toBeInTheDocument();
  });

  it('changing to Explorer calls the API with the override', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildTier')
      .mockResolvedValue({ tier_override: 'explorer', age_tier: 'explorer' });
    renderCard();
    fireEvent.change(screen.getByLabelText('Experience mode'), { target: { value: 'explorer' } });
    await waitFor(() => expect(spy).toHaveBeenCalledWith('child-1', 'explorer'));
  });

  it('changing back to Auto sends null', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildTier')
      .mockResolvedValue({ tier_override: null, age_tier: 'investor' });
    renderCard({ ...BASE_CHILD, tier_override: 'investor', age_tier: 'investor' });
    fireEvent.change(screen.getByLabelText('Experience mode'), { target: { value: 'auto' } });
    await waitFor(() => expect(spy).toHaveBeenCalledWith('child-1', null));
  });

  it('has no axe violations with the experience mode control', async () => {
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('ChildCard Face ID master switch', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders an unchecked Face ID switch by default', () => {
    renderCard();
    const sw = screen.getByLabelText('Face ID sign-in');
    expect(sw).toBeInTheDocument();
    expect(sw).not.toBeChecked();
  });

  it('renders a checked Face ID switch when allowed', () => {
    renderCard({ ...BASE_CHILD, biometric_allowed: true });
    expect(screen.getByLabelText('Face ID sign-in')).toBeChecked();
  });

  it('allows Face ID when toggled on', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildBiometric')
      .mockResolvedValue({ status: 'ok', biometric_allowed: true });
    renderCard();
    fireEvent.click(screen.getByLabelText('Face ID sign-in'));
    await waitFor(() => expect(spy).toHaveBeenCalledWith('child-1', true));
  });
});
