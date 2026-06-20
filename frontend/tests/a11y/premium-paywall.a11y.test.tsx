import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';

function Open() {
  const { open } = usePremiumPaywall();
  useEffect(() => { open({ kind: 'coach', label: 'Coach Penny' }); }, [open]);
  return null;
}

describe('a11y: PremiumPaywall', () => {
  it('no axe violations when open', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={qc}><PremiumPaywallProvider><Open /></PremiumPaywallProvider></QueryClientProvider>);
    // Radix renders the Sheet in a portal (outside `container`), so scan document.body.
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
