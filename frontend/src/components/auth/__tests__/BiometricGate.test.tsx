import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

const bio = vi.hoisted(() => ({
  isAvailable: vi.fn(),
  verify: vi.fn(),
  read: vi.fn(),
  enroll: vi.fn(),
  clear: vi.fn(),
  getDeviceId: vi.fn(() => 'dev-1'),
  getBioAccounts: vi.fn(),
  removeBioAccount: vi.fn(),
}));
vi.mock('@/lib/biometric', () => ({
  biometric: { isAvailable: bio.isAvailable, verify: bio.verify, read: bio.read, enroll: bio.enroll, clear: bio.clear },
  getDeviceId: () => bio.getDeviceId(),
  getBioAccounts: () => bio.getBioAccounts(),
  removeBioAccount: (k: string) => bio.removeBioAccount(k),
}));
const exchange = vi.hoisted(() => vi.fn());
vi.mock('@/api/auth', () => ({ authApi: { biometricExchange: (...a: unknown[]) => exchange(...a) } }));
vi.mock('@/api/parent', () => ({ parentApi: { biometricExchange: vi.fn() } }));

vi.mock('@capacitor/app', () => ({
  App: { addListener: () => Promise.resolve({ remove: vi.fn() }) },
}));

import { BiometricGate } from '../BiometricGate';

function renderGate() {
  return render(
    <MemoryRouter>
      <BiometricGate><div>APP CONTENT</div></BiometricGate>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  bio.isAvailable.mockResolvedValue(true);
  bio.getBioAccounts.mockReturnValue([{ key: 'child:1', label: 'Maya', kind: 'child' }]);
  bio.getDeviceId.mockReturnValue('dev-1');
});
afterEach(() => vi.useRealTimers());

describe('BiometricGate (SP-Bio)', () => {
  it('renders children directly when no accounts enrolled', async () => {
    bio.getBioAccounts.mockReturnValue([]);
    renderGate();
    expect(await screen.findByText('APP CONTENT')).toBeInTheDocument();
  });

  it('renders children when biometric unavailable', async () => {
    bio.isAvailable.mockResolvedValue(false);
    renderGate();
    expect(await screen.findByText('APP CONTENT')).toBeInTheDocument();
  });

  it('locks on launch and unlocks via verify+read+exchange', async () => {
    bio.verify.mockResolvedValue(true);
    bio.read.mockResolvedValue('secret-1');
    exchange.mockResolvedValue({ secret: 'rotated-1' });
    renderGate();
    const btn = await screen.findByRole('button', { name: /maya/i });
    expect(screen.queryByText('APP CONTENT')).toBeNull();
    fireEvent.click(btn);
    await waitFor(() => expect(screen.getByText('APP CONTENT')).toBeInTheDocument());
    expect(exchange).toHaveBeenCalledWith('dev-1', 'secret-1');
    expect(bio.enroll).toHaveBeenCalledWith('child:1', 'Maya', 'rotated-1');
  });

  it('forgets a dead credential on 401 and shows sign-in', async () => {
    bio.verify.mockResolvedValue(true);
    bio.read.mockResolvedValue('secret-1');
    exchange.mockRejectedValue(new Error('401'));
    bio.getBioAccounts.mockReturnValueOnce([{ key: 'child:1', label: 'Maya', kind: 'child' }]).mockReturnValue([]);
    renderGate();
    fireEvent.click(await screen.findByRole('button', { name: /maya/i }));
    await waitFor(() => expect(bio.clear).toHaveBeenCalledWith('child:1'));
    expect(bio.removeBioAccount).toHaveBeenCalledWith('child:1');
  });

  it('stays locked when biometric verify is cancelled', async () => {
    bio.verify.mockResolvedValue(false);
    renderGate();
    fireEvent.click(await screen.findByRole('button', { name: /maya/i }));
    await waitFor(() => expect(bio.verify).toHaveBeenCalled());
    expect(screen.queryByText('APP CONTENT')).toBeNull();
  });

  it('has no axe violations when locked', async () => {
    const { container } = renderGate();
    await screen.findByRole('button', { name: /maya/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
