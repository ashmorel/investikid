import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { consentApi } from '@/api/consent';
import ConsentVerify from '../ConsentVerify';

vi.mock('@/api/consent', () => ({
  consentApi: {
    verify: vi.fn(() => Promise.resolve({ username: 'sophie', age: 9, country_code: 'GB' })),
    decide: vi.fn(() => Promise.resolve({ status: 'ok', decision: 'approve' })),
  },
}));

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/consent/verify?token=abc']}>
        <ConsentVerify />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ConsentVerify', () => {
  it('gates Approve behind the guardian attestation checkbox', async () => {
    const user = userEvent.setup();
    renderPage();

    const approve = await screen.findByRole('button', { name: /approve/i });
    expect(approve).toBeDisabled();

    const checkbox = screen.getByRole('checkbox', { name: /parent or legal guardian/i });
    await user.click(checkbox);
    expect(approve).toBeEnabled();

    await user.click(approve);
    expect(consentApi.decide).toHaveBeenCalledWith('abc', 'approve', true);
  });

  it('allows Decline without the checkbox', async () => {
    const user = userEvent.setup();
    renderPage();

    const decline = await screen.findByRole('button', { name: /decline/i });
    expect(decline).toBeEnabled();

    await user.click(decline);
    expect(consentApi.decide).toHaveBeenCalledWith('abc', 'decline', false);
  });

  it('has no accessibility violations on the decision screen', async () => {
    const { container } = renderPage();
    await screen.findByRole('button', { name: /approve/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
