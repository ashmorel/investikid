import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';

function Trigger() {
  const { open } = usePremiumPaywall();
  return <button onClick={() => open({ kind: 'level', label: 'Investing Basics' })}>lock</button>;
}

describe('PremiumPaywall', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('opens with benefits and requests unlock', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ status: 'sent' }), { status: 200 }));
    render(<PremiumPaywallProvider><Trigger /></PremiumPaywallProvider>);
    await userEvent.click(screen.getByText('lock'));
    expect(await screen.findByText(/premium unlocks/i)).toBeInTheDocument();
    expect(screen.getByText(/coach penny/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    await waitFor(() => expect(screen.getByText(/let your grown-up know|told them/i)).toBeInTheDocument());
  });
});
