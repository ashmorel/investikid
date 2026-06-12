import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { DeleteAccountCard } from '../DeleteAccountCard';
import { parentApi } from '@/api/parent';
import { ApiError } from '@/api/client';

const navigateMock = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock('@/api/parent', () => ({
  parentApi: {
    deleteAccount: vi.fn(),
  },
}));

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const removeQueries = vi.spyOn(qc, 'clear');
  const utils = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DeleteAccountCard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...utils, removeQueries };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(parentApi.deleteAccount).mockResolvedValue({ status: 'ok', children_deleted: 2 });
});

async function openDialog() {
  fireEvent.click(screen.getByRole('button', { name: /delete my account/i }));
  return screen.findByRole('dialog');
}

describe('DeleteAccountCard', () => {
  it('renders the delete button and the billing warning', () => {
    renderCard();
    expect(screen.getByRole('button', { name: /delete my account/i })).toBeInTheDocument();
    expect(screen.getByText(/does not cancel billing/i)).toBeInTheDocument();
  });

  it('opening the dialog shows the email-confirm input with Delete disabled when empty', async () => {
    renderCard();
    await openDialog();
    expect(screen.getByLabelText(/type your email to confirm/i)).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /^delete account$/i });
    expect(confirmBtn).toBeDisabled();
  });

  it('submitting calls deleteAccount with the typed email and navigates on success', async () => {
    const { removeQueries } = renderCard();
    await openDialog();
    fireEvent.change(screen.getByLabelText(/type your email to confirm/i), {
      target: { value: 'parent@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^delete account$/i }));
    await waitFor(() =>
      expect(parentApi.deleteAccount).toHaveBeenCalledWith('parent@example.com'),
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/parent/login', { replace: true }));
    expect(removeQueries).toHaveBeenCalled();
  });

  it('shows an inline error and does not navigate when the email does not match (400)', async () => {
    vi.mocked(parentApi.deleteAccount).mockRejectedValue(
      new ApiError(400, 'confirm_email does not match'),
    );
    renderCard();
    await openDialog();
    fireEvent.change(screen.getByLabelText(/type your email to confirm/i), {
      target: { value: 'wrong@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^delete account$/i }));
    expect(await screen.findByText(/doesn't match your account email/i)).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it('has no axe violations with the dialog open', async () => {
    const { container } = renderCard();
    await openDialog();
    expect(await axe(container)).toHaveNoViolations();
  });
});
