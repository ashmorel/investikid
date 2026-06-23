import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import type { ShopState } from '@/api/cosmetics';
import Shop from '../Shop';

let shop: ShopState;
const buyPost = vi.fn();
vi.mock('@/api/client', () => ({
  apiFetch: (path: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      buyPost(path);
      return Promise.resolve({ status: 'ok', coins: 0 });
    }
    return Promise.resolve(shop);
  },
}));

function renderShop() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>
        <MemoryRouter>
          <Shop />
        </MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

const item = (over: Partial<ShopState['items'][0]>): ShopState['items'][0] => ({
  id: 'i1', slug: 'party_hat', name: 'Party Hat', emoji: '🥳', type: 'accessory', coin_cost: 50,
  is_premium: false, owned: false, equipped: false, can_buy: true, ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  shop = { coins: 120, items: [item({})] };
});

describe("Penny's Shop (m8)", () => {
  it('shows the coin balance and item states', async () => {
    shop = {
      coins: 120,
      items: [
        item({}),
        item({ id: 'i2', slug: 'crown', name: 'Golden Crown', coin_cost: 300, can_buy: false }),
        item({ id: 'i3', slug: 'bow', name: 'Big Bow', owned: true, equipped: true, can_buy: false }),
      ],
    };
    renderShop();
    expect(await screen.findByLabelText('120 coins')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Keep saving' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Take off' })).toBeEnabled();
  });

  it('buys after the confirm dialog', async () => {
    renderShop();
    fireEvent.click(await screen.findByRole('button', { name: 'Buy' }));
    expect(screen.getByText(/buy party hat\?/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^confirm$/i }));
    await waitFor(() => expect(buyPost).toHaveBeenCalledWith('/cosmetics/i1/buy'));
  });
  it('equips an owned item', async () => {
    shop = { coins: 10, items: [item({ owned: true, can_buy: false })] };
    renderShop();
    fireEvent.click(await screen.findByRole('button', { name: 'Wear it' }));
    await waitFor(() => expect(buyPost).toHaveBeenCalledWith('/cosmetics/i1/equip'));
  });

  it('has no axe violations', async () => {
    const { container } = renderShop();
    await screen.findByRole('button', { name: 'Buy' });
    expect(await axe(container)).toHaveNoViolations();
  });
});
