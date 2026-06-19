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
type Mod = { id: string; topic: string; title: string; market_code: string; order_index: number };
type Lvl = { id: string; module_id: string; title: string; order_index: number };

let marketsData: MarketSummary[] = [
  { code: 'GB', name: 'United Kingdom', has_content: true },
  { code: 'US', name: 'United States', has_content: false },
];
let briefData: Brief | undefined;
let briefStatus = { isLoading: false, isError: false };
let modulesData: Mod[] = [];
let levelsByModule: Record<string, Lvl[]> = {};
const mockGenerateMarket = vi.fn();
const idleMutation = { mutate: vi.fn(), isPending: false, isError: false, isSuccess: false, data: undefined, error: null as unknown };

// Captures the levelId passed to the per-level hook factory so the test can
// assert the generate-market mutation fires with { levelId, source_level_id }.
vi.mock('@/api/admin', () => ({
  useMarketBrief: () => ({ data: briefData, ...briefStatus }),
  useGenerateMarketBrief: () => ({ ...idleMutation, mutate: mockGenerateBrief }),
  useUpdateMarketBrief: () => ({ ...idleMutation, mutate: mockUpdateBrief }),
  useVerifyMarketBrief: () => ({ ...idleMutation, mutate: mockVerifyBrief }),
  useScaffoldMarket: () => ({ ...idleMutation, mutate: mockScaffold }),
  useModules: () => ({ data: modulesData }),
  useLevels: (moduleId: string) => ({ data: levelsByModule[moduleId] ?? [] }),
  useGenerateMarketLessons: (levelId: string) => ({
    ...idleMutation,
    mutate: (sourceLevelId: string) => mockGenerateMarket({ levelId, source_level_id: sourceLevelId }),
  }),
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
  mockGenerateMarket.mockClear();
  marketsData = [
    { code: 'GB', name: 'United Kingdom', has_content: true },
    { code: 'US', name: 'United States', has_content: false },
  ];
  briefData = undefined;
  briefStatus = { isLoading: false, isError: false };
  modulesData = [];
  levelsByModule = {};
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

  it('generates market lessons for a scaffolded level using the matched GB source level', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    // GB + US each have a "saving" module at order 0 with one level at order 0.
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0 }],
      'us-mod': [{ id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0 }],
    };
    render(<MarketContent />, { wrapper });
    const btn = await screen.findByRole('button', { name: /generate lessons \(from gb\)/i });
    fireEvent.click(btn);
    await waitFor(() =>
      expect(mockGenerateMarket).toHaveBeenCalledWith({ levelId: 'us-lvl', source_level_id: 'gb-lvl' }),
    );
  });
});
