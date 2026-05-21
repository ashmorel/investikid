import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AdminLogin from '../AdminLogin';

const mockSetToken = vi.fn();
vi.mock('@/lib/adminAuth', () => ({
  getAdminToken: () => null,
  setAdminToken: (t: string) => mockSetToken(t),
  clearAdminToken: vi.fn(),
}));

describe('AdminLogin', () => {
  beforeEach(() => { mockSetToken.mockClear(); });

  it('renders token input and submit button', () => {
    render(<AdminLogin onAuthenticated={vi.fn()} />);
    expect(screen.getByLabelText(/admin token/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls onAuthenticated when token is submitted', () => {
    const onAuth = vi.fn();
    render(<AdminLogin onAuthenticated={onAuth} />);
    fireEvent.change(screen.getByLabelText(/admin token/i), { target: { value: 'my-token' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(mockSetToken).toHaveBeenCalledWith('my-token');
    expect(onAuth).toHaveBeenCalled();
  });

  it('does not submit with empty token', () => {
    const onAuth = vi.fn();
    render(<AdminLogin onAuthenticated={onAuth} />);
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(onAuth).not.toHaveBeenCalled();
  });
});
