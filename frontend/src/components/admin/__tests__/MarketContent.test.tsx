import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MarketContent from '../MarketContent';

// ── Mock state shared across hook mocks ──────────────────────────────
const mockGenerateBrief = vi.fn();
const mockUpdateBrief = vi.fn();
const mockVerifyBrief = vi.fn();
const mockScaffold = vi.fn();
const mockPublish = vi.fn();
const mockUnpublish = vi.fn();

type MarketSummary = { code: string; name: string; has_content: boolean };
type Brief = { market_code: string; brief_json: Record<string, unknown>; status: string; model_used: string };

let marketsData: MarketSummary[] = [
  { code: 'GB', name: 'United Kingdom', has_content: true },
  { code: 'US', name: 'United States', has_content: false },
];
let briefData: Brief | undefined;
let briefStatus = { isLoading: false, isError: false };
const idleMutation = { mutate: vi.fn(), isPending: false, isError: false, isSuccess: false, data: undefined, error: null as unknown };

vi.mock('@/api/admin', () => ({
  useMarketBrief: () => ({ data: briefData, ...briefStatus }),
  useGenerateMarketBrief: () => ({ ...idleMutation, mutate: mockGenerateBrief }),
  useUpdateMarketBrief: () => ({ ...idleMutation, mutate: mockUpdateBrief }),
  useVerifyMarketBrief: () => ({ ...idleMutation, mutate: mockVerifyBrief }),
  useScaffoldMarket: () => ({ ...idleMutation, mutate: mockScaffold }),
  useGenerateMarketLessons: () => ({ ...idleMutation, mutate: vi.fn() }),
  usePublishMarket: () => ({ ...idleMutation, mutate: mockPublish }),
  useUnpublishMarket: () => ({ ...idleMutation, mutate: mockUnpublish }),
}));

vi.mock('@/api/market', () => ({
  marketApi: { list: () => Promise.resolve(marketsData) },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockGenerateBrief.mockClear();
  mockVerifyBrief.mockClear();
  mockScaffold.mockClear();
  mockPublish.mockClear();
  mockUnpublish.mockClear();
  marketsData = [
    { code: 'GB', name: 'United Kingdom', has_content: true },
    { code: 'US', name: 'United States', has_content: false },
  ];
  briefData = undefined;
  briefStatus = { isLoading: false, isError: false };
});

describe('MarketContent', () => {
  it('renders the workflow controls', async () => {
    render(<MarketContent />, { wrapper });
    expect(await screen.findByRole('button', { name: /generate brief/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /^market$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /verify brief/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /scaffold from gb/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^publish$/i })).toBeInTheDocument();
  });

  it('disables Scaffold until the brief is verified', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'draft', model_used: 'm' };
    render(<MarketContent />, { wrapper });
    expect(await screen.findByRole('button', { name: /scaffold from gb/i })).toBeDisabled();
  });

  it('enables Scaffold once the brief is verified', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    render(<MarketContent />, { wrapper });
    expect(await screen.findByRole('button', { name: /scaffold from gb/i })).toBeEnabled();
  });

  it('disables Publish once the market is already live', async () => {
    marketsData = [
      { code: 'GB', name: 'United Kingdom', has_content: true },
      { code: 'US', name: 'United States', has_content: true },
    ];
    render(<MarketContent />, { wrapper });
    expect(await screen.findByRole('button', { name: /^publish$/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^unpublish$/i })).toBeEnabled();
  });

  it('allows Publish for an unpublished market (409 surfaces the no-lessons message)', async () => {
    render(<MarketContent />, { wrapper });
    expect(await screen.findByRole('button', { name: /^publish$/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /^unpublish$/i })).toBeDisabled();
  });

  it('calls generateBrief for the selected market', async () => {
    render(<MarketContent />, { wrapper });
    fireEvent.click(await screen.findByRole('button', { name: /generate brief/i }));
    await waitFor(() => expect(mockGenerateBrief).toHaveBeenCalled());
  });
});
