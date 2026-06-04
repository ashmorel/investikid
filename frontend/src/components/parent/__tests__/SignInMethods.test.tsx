import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { SignInMethods } from '../SignInMethods';
import { parentAuthApi } from '@/api/parentAuth';
import { socialIdToken } from '@/lib/socialLogin';

vi.mock('@/api/parentAuth');
vi.mock('@/lib/socialLogin');

function renderComponent() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <SignInMethods />
    </QueryClientProvider>,
  );
}

describe('SignInMethods', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows Connected + Disconnect for Google and Connect for Apple', async () => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([
      { provider: 'google', parent_email: 'p@e.com' },
    ]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByLabelText('Disconnect Google')).toBeInTheDocument();
    });
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByLabelText('Connect Apple')).toBeInTheDocument();
  });

  it('calls socialIdToken + linkProvider + refetches when Connect Apple clicked', async () => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([
      { provider: 'google', parent_email: 'p@e.com' },
    ]);
    vi.mocked(socialIdToken).mockResolvedValue({ idToken: 'tok', nonce: 'n' });
    vi.mocked(parentAuthApi.linkProvider).mockResolvedValue({ status: 'ok' });

    renderComponent();

    await waitFor(() => screen.getByLabelText('Connect Apple'));

    // After clicking Connect, listIdentities should be called again for refetch
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([
      { provider: 'google', parent_email: 'p@e.com' },
      { provider: 'apple', parent_email: 'p@e.com' },
    ]);

    fireEvent.click(screen.getByLabelText('Connect Apple'));

    await waitFor(() => {
      expect(socialIdToken).toHaveBeenCalledWith('apple');
      expect(parentAuthApi.linkProvider).toHaveBeenCalledWith('apple', 'tok', 'n');
    });

    await waitFor(() => {
      expect(parentAuthApi.listIdentities).toHaveBeenCalledTimes(2);
    });
  });

  it('calls unlinkProvider + refetches when Disconnect Google clicked', async () => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([
      { provider: 'google', parent_email: 'p@e.com' },
    ]);
    vi.mocked(parentAuthApi.unlinkProvider).mockResolvedValue({ status: 'ok' });

    renderComponent();

    await waitFor(() => screen.getByLabelText('Disconnect Google'));

    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([]);

    fireEvent.click(screen.getByLabelText('Disconnect Google'));

    await waitFor(() => {
      expect(parentAuthApi.unlinkProvider).toHaveBeenCalledWith('google');
    });

    await waitFor(() => {
      expect(parentAuthApi.listIdentities).toHaveBeenCalledTimes(2);
    });
  });

  it('shows 409 conflict error message', async () => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([]);
    vi.mocked(socialIdToken).mockResolvedValue({ idToken: 'tok', nonce: 'n' });
    vi.mocked(parentAuthApi.linkProvider).mockRejectedValue({ status: 409 });

    renderComponent();

    await waitFor(() => screen.getByLabelText('Connect Apple'));

    fireEvent.click(screen.getByLabelText('Connect Apple'));

    await waitFor(() => {
      expect(
        screen.getByText('That account is already connected to a different parent.'),
      ).toBeInTheDocument();
    });
  });

  it('no a11y violations', async () => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([
      { provider: 'google', parent_email: 'p@e.com' },
    ]);

    const { container } = renderComponent();

    await waitFor(() => screen.getByLabelText('Disconnect Google'));

    expect(await axe(container)).toHaveNoViolations();
  });
});
