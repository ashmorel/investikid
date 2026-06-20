import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Signup from '@/pages/child/Signup';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/signup']}>
        <Routes>
          <Route path="/signup" element={<Signup />} />
          <Route path="/home" element={<div>Home Page</div>} />
          <Route path="/pending-consent" element={<div>Pending Consent</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function fillDob(dateStr: string) {
  const [y, m, d] = dateStr.split('-');
  await userEvent.selectOptions(screen.getByLabelText('Year'), String(Number(y)));
  await userEvent.selectOptions(screen.getByLabelText('Month'), String(Number(m)));
  await userEvent.selectOptions(screen.getByLabelText('Day'), String(Number(d)));
}

beforeEach(() => { vi.restoreAllMocks(); vi.spyOn(globalThis, 'fetch'); });

describe('Signup step 1', () => {
  it('shows under-threshold banner for UK 11', async () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /let's get you set up/i })).toBeInTheDocument();
    await fillDob('2015-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'GB');
    expect(screen.getByText(/rule where you live/i)).toBeInTheDocument();
  });

  it('shows over-threshold banner for US 14', async () => {
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    expect(screen.getByText(/you can set up your own account/i)).toBeInTheDocument();
  });

  it('shows under-threshold banner for IE 14 (16 threshold)', async () => {
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'IE');
    expect(screen.getByText(/rule where you live/i)).toBeInTheDocument();
  });

  it('Next is disabled until both fields filled', async () => {
    renderPage();
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
    await fillDob('2012-01-01');
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    expect(screen.getByRole('button', { name: /next/i })).toBeEnabled();
  });
});

describe('Signup step 2 — under-threshold flow', () => {
  it('parent_email field appears, redirects to /pending-consent on success', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'pending_consent', user_id: 'u1' }), { status: 201 }),
    );
    renderPage();
    await fillDob('2015-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'GB');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(screen.getByRole('heading', { name: /let's get you set up/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/parent email/i)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^email$/i), 'kid@example.com');
    await userEvent.type(screen.getByLabelText(/username/i), 'kid');
    await userEvent.type(screen.getByLabelText(/^password/i), 'SecurePass123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'SecurePass123!');
    await userEvent.type(screen.getByLabelText(/parent email/i), 'parent@example.com');
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => expect(screen.getByText('Pending Consent')).toBeInTheDocument());
  });
});

describe('Signup step 2 — over-threshold flow', () => {
  it('no parent_email field, register+login redirects to /home', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce(  // register
        new Response(JSON.stringify({
          id: 'u1', email: 'kid@example.com', username: 'kid', dob: '2012-01-01',
          country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
          parent_email: null, created_at: '2026-04-29T00:00:00Z',
        }), { status: 201 }),
      )
      .mockResolvedValueOnce(  // auto-login
        new Response(JSON.stringify({ token_type: 'bearer' }), { status: 200 }),
      );
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(screen.queryByLabelText(/parent email/i)).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^email$/i), 'kid@example.com');
    await userEvent.type(screen.getByLabelText(/username/i), 'kid');
    await userEvent.type(screen.getByLabelText(/^password/i), 'SecurePass123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'SecurePass123!');
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => expect(screen.getByText('Home Page')).toBeInTheDocument());
  });
});

describe('Signup step 2 — error handling', () => {
  it('409 username conflict shows field-level error', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Username already taken' }), { status: 409 }),
    );
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.type(screen.getByLabelText(/^email$/i), 'a@x.com');
    await userEvent.type(screen.getByLabelText(/username/i), 'taken');
    await userEvent.type(screen.getByLabelText(/^password/i), 'SecurePass123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'SecurePass123!');
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /create account/i }));
    expect(await screen.findByText(/Username already taken/i)).toBeInTheDocument();
  });

  it('mismatched passwords block submit and show an error', async () => {
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.type(screen.getByLabelText(/^email$/i), 'a@x.com');
    await userEvent.type(screen.getByLabelText(/username/i), 'user1');
    await userEvent.type(screen.getByLabelText(/^password/i), 'SecurePass123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Different123!');
    await userEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeDisabled();
  });
});

describe('Signup step 2 — privacy notice', () => {
  it('opens the privacy notice in a modal without leaving the form', async () => {
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.type(screen.getByLabelText(/username/i), 'user1');
    await userEvent.click(screen.getByRole('button', { name: /privacy notice/i }));
    // Modal content appears...
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/what is investikid/i)).toBeInTheDocument();
    // ...and the form is still mounted (username retained)
    expect(screen.getByLabelText(/username/i)).toHaveValue('user1');
  });
});

describe('Signup step 2 — back button', () => {
  it('back button preserves step 1 values', async () => {
    renderPage();
    await fillDob('2012-01-01');
    await userEvent.selectOptions(screen.getByLabelText(/country/i), 'US');
    await userEvent.click(screen.getByRole('button', { name: /next/i }));
    await userEvent.click(screen.getByRole('button', { name: /back/i }));
    expect(screen.getByLabelText('Year')).toHaveValue('2012');
    expect(screen.getByLabelText(/country/i)).toHaveValue('US');
  });
});
