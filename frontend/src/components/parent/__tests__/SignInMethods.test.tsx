import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { SignInMethods } from '../SignInMethods';
import { parentAuthApi } from '@/api/parentAuth';
import { parentApi } from '@/api/parent';
import { socialIdToken } from '@/lib/socialLogin';
import { addBioAccount, biometric, getBioAccounts, removeBioAccount } from '@/lib/biometric';

vi.mock('@/api/parentAuth');
vi.mock('@/lib/socialLogin');
vi.mock('@/api/parent', () => ({
  parentApi: {
    biometricEnroll: vi.fn(async () => ({ secret: 'srv-secret' })),
    biometricUnenroll: vi.fn(async () => ({})),
  },
}));
vi.mock('@/lib/biometric', () => ({
  biometric: {
    isAvailable: vi.fn(async () => true),
    verify: vi.fn(async () => true),
    enroll: vi.fn(async () => {}),
    clear: vi.fn(async () => {}),
  },
  getDeviceId: vi.fn(() => 'pdev-1'),
  getBioAccounts: vi.fn(() => []),
  addBioAccount: vi.fn(),
  removeBioAccount: vi.fn(),
}));

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

describe('SignInMethods Face ID self-enroll', () => {
  beforeEach(() => {
    vi.mocked(parentAuthApi.listIdentities).mockResolvedValue([]);
    vi.mocked(biometric.isAvailable).mockResolvedValue(true);
    vi.mocked(biometric.verify).mockResolvedValue(true);
    vi.mocked(parentApi.biometricEnroll).mockResolvedValue({ secret: 'srv-secret' });
    vi.mocked(getBioAccounts).mockReturnValue([]);
  });

  it('enrolls — verify, parent enroll, keychain write, registry add', async () => {
    renderComponent();
    const checkbox = await screen.findByRole('checkbox', { name: /face id sign-in/i });
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(biometric.verify).toHaveBeenCalled();
      expect(parentApi.biometricEnroll).toHaveBeenCalledWith('pdev-1', 'Parent');
      expect(biometric.enroll).toHaveBeenCalledWith('parent', 'Parent', 'srv-secret');
      expect(addBioAccount).toHaveBeenCalledWith({ key: 'parent', label: 'Parent', kind: 'parent' });
    });
  });

  it('unenrolls — parent unenroll, keychain clear, registry remove', async () => {
    vi.mocked(getBioAccounts).mockReturnValue([{ key: 'parent', label: 'Parent', kind: 'parent' }]);
    renderComponent();
    const checkbox = await screen.findByRole('checkbox', { name: /face id sign-in/i });
    expect(checkbox).toBeChecked();
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(parentApi.biometricUnenroll).toHaveBeenCalledWith('pdev-1');
      expect(biometric.clear).toHaveBeenCalledWith('parent');
      expect(removeBioAccount).toHaveBeenCalledWith('parent');
    });
  });

  it('hides the Face ID toggle when hardware is unavailable', async () => {
    vi.mocked(biometric.isAvailable).mockResolvedValue(false);
    renderComponent();
    await waitFor(() => screen.getByLabelText('Connect Apple'));
    expect(screen.queryByRole('checkbox', { name: /face id sign-in/i })).toBeNull();
  });
});
