import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';

vi.mock('@/api/cosmetics', () => ({
  useEquippedCosmetics: () => ({ accessories: ['party_hat'], skin: 'skin_sky', background: null }),
}));

import { TopNav } from '../TopNav';

function renderNav() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter><TopNav username="Sam" /></MemoryRouter>
    </QueryClientProvider>
  );
}

describe('TopNav', () => {
  it('shows the child name and a Penny avatar (svg), not the brand image', () => {
    const { container } = renderNav();
    // Check that there's an SVG with the expected viewBox (Penny)
    expect(container.querySelector('svg[viewBox="0 0 56 56"]')).toBeTruthy();
    // Check that the old brand image is gone
    expect(container.querySelector('img[src="/icons/icon-192.png"]')).toBeNull();
    // Check that the username appears in the top-left link
    const link = screen.getByRole('link', { name: /Home — Sam/i });
    expect(link).toHaveAttribute('href', '/home');
  });

  it('the home link is accessible and points to /home', () => {
    renderNav();
    const link = screen.getByRole('link', { name: /Home — Sam/i });
    expect(link).toHaveAttribute('href', '/home');
  });

  it('has no axe violations', async () => {
    expect(await axe(renderNav().container)).toHaveNoViolations();
  });
});
