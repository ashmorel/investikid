import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminSettings from '../AdminSettings';

// ── Mock state shared across hook mocks ──────────────────────────────
const mockMutate = vi.fn();
const mockReset = vi.fn();

let settingsData: { alert_emails: string[] } | undefined;
let mutationState = {
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null as unknown,
};

vi.mock('@/api/admin', () => ({
  useAdminSettings: () => ({
    data: settingsData,
    isLoading: false,
    isError: false,
  }),
  useUpdateAdminSettings: () => ({
    mutate: mockMutate,
    reset: mockReset,
    ...mutationState,
  }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockMutate.mockClear();
  mockReset.mockClear();
  settingsData = undefined;
  mutationState = { isPending: false, isError: false, isSuccess: false, error: null };
});

describe('AdminSettings', () => {
  it('renders existing emails from query data', () => {
    settingsData = { alert_emails: ['alice@example.com', 'bob@example.com'] };
    render(<AdminSettings />, { wrapper });
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByText('bob@example.com')).toBeInTheDocument();
  });

  it('shows empty-list note when no emails are configured', () => {
    settingsData = { alert_emails: [] };
    render(<AdminSettings />, { wrapper });
    expect(screen.getByText(/alerts are currently off/i)).toBeInTheDocument();
  });

  it('typing and clicking Add shows a new email row', () => {
    settingsData = { alert_emails: [] };
    render(<AdminSettings />, { wrapper });

    fireEvent.change(screen.getByLabelText(/add email address/i), { target: { value: 'new@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

    expect(screen.getByText('new@example.com')).toBeInTheDocument();
  });

  it('rejects an invalid email and shows an error', () => {
    settingsData = { alert_emails: [] };
    render(<AdminSettings />, { wrapper });

    fireEvent.change(screen.getByLabelText(/add email address/i), { target: { value: 'not-an-email' } });
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

    expect(screen.getByText(/not a valid email/i)).toBeInTheDocument();
    expect(screen.queryByText('not-an-email')).not.toBeInTheDocument();
  });

  it('Remove button drops the email from the list', () => {
    settingsData = { alert_emails: ['alice@example.com'] };
    render(<AdminSettings />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /remove alice@example.com/i }));

    expect(screen.queryByText('alice@example.com')).not.toBeInTheDocument();
    expect(screen.getByText(/alerts are currently off/i)).toBeInTheDocument();
  });

  it('Save calls useUpdateAdminSettings with the current email list', async () => {
    settingsData = { alert_emails: ['alice@example.com'] };
    render(<AdminSettings />, { wrapper });

    // Add a second email
    fireEvent.change(screen.getByLabelText(/add email address/i), { target: { value: 'carol@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith({
        alert_emails: ['alice@example.com', 'carol@example.com'],
      });
    });
  });

  it('shows saving state when isPending', () => {
    settingsData = { alert_emails: [] };
    mutationState = { isPending: true, isError: false, isSuccess: false, error: null };
    render(<AdminSettings />, { wrapper });
    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
  });

  it('shows success feedback after save', () => {
    settingsData = { alert_emails: [] };
    mutationState = { isPending: false, isError: false, isSuccess: true, error: null };
    render(<AdminSettings />, { wrapper });
    expect(screen.getByText(/settings saved/i)).toBeInTheDocument();
  });

  it('shows 422 error message on validation failure', () => {
    settingsData = { alert_emails: [] };
    mutationState = { isPending: false, isError: true, isSuccess: false, error: { status: 422 } };
    render(<AdminSettings />, { wrapper });
    expect(screen.getByText(/invalid data/i)).toBeInTheDocument();
  });
});
