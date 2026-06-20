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
type Lvl = { id: string; module_id: string; title: string; order_index: number; lesson_count: number };

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

// Batch-generation runners (Task 5). `mockGenerateModuleHook` captures the
// moduleId + include_populated arg from the per-module hook mutation;
// `mockGenerateModuleFn` stands in for the plain helper used by the
// market-wide sequential runner. Default: resolve an empty batch result.
type ModuleBatchResult = {
  levels: { level_id: string; status: string; created: number; skipped: number }[];
  generated: number;
  skipped_populated: number;
  skipped_no_source: number;
  errored: number;
};
const emptyBatch: ModuleBatchResult = {
  levels: [],
  generated: 0,
  skipped_populated: 0,
  skipped_no_source: 0,
  errored: 0,
};
const mockGenerateModuleHook = vi.fn();
const mockGenerateModuleFn = vi.fn((_id: string, _incl: boolean) => Promise.resolve(emptyBatch));

// Suggestion-flow mock state (driven per test).
const mockSuggest = vi.fn();
const mockCreateSuggestion = vi.fn();
const mockGenerateNative = vi.fn();
type Suggestion = {
  title: string;
  topic: string;
  rationale: string;
  action: 'add' | 'replace';
  replaces: string | null;
  suggested_concepts: string[];
};
let suggestData: Suggestion[] | undefined = undefined;
let suggestState = { isPending: false, isError: false, isSuccess: false };
let createResult: { module_id: string; level_id: string; suggested_concepts: string[] } | undefined = undefined;

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
  useGenerateModuleLessons: (moduleId: string) => ({
    ...idleMutation,
    mutate: (include_populated: boolean) => mockGenerateModuleHook({ moduleId, include_populated }),
  }),
  generateModuleLessons: (moduleId: string, include_populated: boolean) =>
    mockGenerateModuleFn(moduleId, include_populated),
  useSuggestModules: () => ({ ...idleMutation, ...suggestState, data: suggestData, mutate: mockSuggest }),
  useCreateModuleFromSuggestion: () => ({
    ...idleMutation,
    data: createResult,
    mutate: mockCreateSuggestion,
  }),
  useGenerateNativeLessons: (levelId: string) => ({
    ...idleMutation,
    mutate: (concepts: string[]) => mockGenerateNative({ levelId, concepts }),
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
  mockGenerateModuleHook.mockClear();
  mockGenerateModuleFn.mockClear();
  mockGenerateModuleFn.mockResolvedValue(emptyBatch);
  mockSuggest.mockClear();
  mockCreateSuggestion.mockClear();
  mockGenerateNative.mockClear();
  suggestData = undefined;
  suggestState = { isPending: false, isError: false, isSuccess: false };
  createResult = undefined;
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
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 }],
      'us-mod': [{ id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 3 }],
    };
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<MarketContent />, { wrapper });
    // The US level already has 3 published lessons, so the button is a
    // "Regenerate (replace)" heads-up that confirms before generating.
    const btn = await screen.findByRole('button', { name: /regenerate \(replace\)/i });
    fireEvent.click(btn);
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() =>
      expect(mockGenerateMarket).toHaveBeenCalledWith({ levelId: 'us-lvl', source_level_id: 'gb-lvl' }),
    );
    confirmSpy.mockRestore();
  });

  it('shows a published-lesson badge per level based on lesson_count', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [
        { id: 'gb-lvl-a', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 },
        { id: 'gb-lvl-b', module_id: 'gb-mod', title: 'More', order_index: 1, lesson_count: 0 },
      ],
      'us-mod': [
        { id: 'us-lvl-a', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 3 },
        { id: 'us-lvl-b', module_id: 'us-mod', title: 'More (US)', order_index: 1, lesson_count: 0 },
      ],
    };
    render(<MarketContent />, { wrapper });
    expect(await screen.findByText('3 published')).toBeInTheDocument();
    expect(screen.getByText('No lessons yet')).toBeInTheDocument();
  });

  it('per-module "Generate all levels" runs the module batch (include_populated false)', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 }],
      'us-mod': [{ id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 0 }],
    };
    render(<MarketContent />, { wrapper });
    fireEvent.click(await screen.findByRole('button', { name: /generate all levels/i }));
    await waitFor(() =>
      expect(mockGenerateModuleHook).toHaveBeenCalledWith({ moduleId: 'us-mod', include_populated: false }),
    );
  });

  it('market-wide "Generate all" runs each module batch sequentially (one call per module)', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 }],
      'us-mod': [{ id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 0 }],
    };
    render(<MarketContent />, { wrapper });
    fireEvent.click(await screen.findByRole('button', { name: /^generate all$/i }));
    await waitFor(() => expect(mockGenerateModuleFn).toHaveBeenCalledTimes(1));
    expect(mockGenerateModuleFn).toHaveBeenCalledWith('us-mod', false);
  });

  it('creates a module from a suggestion, then generates native lessons with its concepts', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    suggestData = [
      {
        title: 'Sales tax basics',
        topic: 'tax',
        rationale: 'US has sales tax, not VAT.',
        action: 'add',
        replaces: null,
        suggested_concepts: ['sales tax', 'receipts'],
      },
    ];
    suggestState = { isPending: false, isError: false, isSuccess: true };
    const first = render(<MarketContent />, { wrapper });

    const createBtn = await screen.findByRole('button', { name: /create this module/i });
    fireEvent.click(createBtn);
    expect(mockCreateSuggestion).toHaveBeenCalledWith(suggestData[0]);
    first.unmount();

    // Drive the create result so the native-generate control appears.
    createResult = { module_id: 'us-mod', level_id: 'us-lvl', suggested_concepts: ['sales tax', 'receipts'] };
    render(<MarketContent />, { wrapper });
    const genBtn = await screen.findByRole('button', { name: /^generate lessons$/i });
    fireEvent.click(genBtn);
    expect(mockGenerateNative).toHaveBeenCalledWith({
      levelId: 'us-lvl',
      concepts: ['sales tax', 'receipts'],
    });
  });
});
