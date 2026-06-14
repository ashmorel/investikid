import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const navigate = vi.fn();
vi.mock('react-router-dom', async (o) => ({
  ...(await o() as object),
  useNavigate: () => navigate,
  useSearchParams: () => [new URLSearchParams('token=abc'), vi.fn()],
}));

const { decide } = vi.hoisted(() => ({
  decide: vi.fn().mockResolvedValue({ status: 'ok', decision: 'approve' }),
}));
vi.mock('@/api/consent', () => ({
  consentApi: {
    verify: vi.fn().mockResolvedValue({ username: 'Yaz', age: 9, country_code: 'GB' }),
    decide,
  },
}));

import ConsentVerify from '../ConsentVerify';

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/consent/verify?token=abc']}>
        <ConsentVerify />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ConsentVerify approve redirect', () => {
  it('navigates to /parent after a successful approve', async () => {
    const user = userEvent.setup();
    renderPage();

    const checkbox = await screen.findByRole('checkbox', { name: /parent or legal guardian/i });
    await user.click(checkbox);

    const approve = screen.getByRole('button', { name: /approve/i });
    await user.click(approve);

    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/parent'));
  });
});
