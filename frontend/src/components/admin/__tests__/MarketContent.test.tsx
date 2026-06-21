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
type Lvl = { id: string; module_id: string; title: string; order_index: number; lesson_count: number; draft_count?: number };

let marketsData: MarketSummary[] = [
  { code: 'GB', name: 'United Kingdom', has_content: true },
  { code: 'US', name: 'United States', has_content: false },
];
let briefData: Brief | undefined;
let briefStatus = { isLoading: false, isError: false };
let modulesData: Mod[] = [];
let levelsByModule: Record<string, Lvl[]> = {};
const idleMutation = { mutate: vi.fn(), isPending: false, isError: false, isSuccess: false, data: undefined, error: null as unknown };

// Batch-generation runners (Task 5). `mockGenerateModuleHook` captures the
// moduleId + include_populated arg from the per-module hook mutation;
// `mockGenerateModuleFn` stands in for the plain helper used by the
// market-wide sequential runner. Default: resolve an empty batch result.
type ModuleBatchResult = {
  levels: { level_id: string; status: string; created: number; skipped: number }[];
  generated: number;
  skipped_populated: number;
  skipped_has_drafts: number;
  skipped_no_source: number;
  skipped_no_concepts: number;
  errored: number;
};
const emptyBatch: ModuleBatchResult = {
  levels: [],
  generated: 0,
  skipped_populated: 0,
  skipped_has_drafts: 0,
  skipped_no_source: 0,
  skipped_no_concepts: 0,
  errored: 0,
};
const mockGenerateModuleHook = vi.fn();
const mockGenerateModuleFn = vi.fn((_id: string, _incl: boolean) => Promise.resolve(emptyBatch));

// Publish-curriculum mock state.
const mockPublishCurriculum = vi.fn();
let curriculumData: { proposal_id: string } | null = null;

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

// Stub CurriculumPanel — it calls useCurriculum which is not in the @/api/admin mock.
vi.mock('../CurriculumPanel', () => ({
  default: () => <div data-testid="curriculum-panel-stub" />,
}));

// Stub LessonDraftReview so the inline panel renders without needing
// full draft-API hooks wired up in this test file.
vi.mock('../LessonDraftReview', () => ({
  default: ({ levelId }: { levelId: string }) => (
    <div data-testid={`draft-review-${levelId}`}>Draft review panel</div>
  ),
}));

vi.mock('@/api/admin', () => ({
  useMarketBrief: () => ({ data: briefData, ...briefStatus }),
  useGenerateMarketBrief: () => ({ ...idleMutation, mutate: mockGenerateBrief }),
  useUpdateMarketBrief: () => ({ ...idleMutation, mutate: mockUpdateBrief }),
  useVerifyMarketBrief: () => ({ ...idleMutation, mutate: mockVerifyBrief }),
  useScaffoldMarket: () => ({ ...idleMutation, mutate: mockScaffold }),
  useModules: () => ({ data: modulesData }),
  useLevels: (moduleId: string) => ({ data: levelsByModule[moduleId] ?? [] }),
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
  usePublishCurriculum: () => ({ ...idleMutation, mutate: mockPublishCurriculum }),
  useCurriculum: () => ({ data: curriculumData }),
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
  mockPublishCurriculum.mockClear();
  mockGenerateModuleHook.mockClear();
  mockGenerateModuleFn.mockClear();
  mockGenerateModuleFn.mockResolvedValue(emptyBatch);
  mockSuggest.mockClear();
  mockCreateSuggestion.mockClear();
  mockGenerateNative.mockClear();
  suggestData = undefined;
  suggestState = { isPending: false, isError: false, isSuccess: false };
  createResult = undefined;
  curriculumData = null;
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

  it('renders the Brief + Curriculum panel for GB (no longer a source-only wall)', async () => {
    // Default market list has GB first but the component defaults to the first non-GB
    // market. Flip marketsData so GB is the only option, forcing code === 'GB'.
    marketsData = [{ code: 'GB', name: 'United Kingdom', has_content: true }];

    render(<MarketContent />, { wrapper });

    // Brief heading is present for GB
    expect(await screen.findByText('1. Market brief')).toBeInTheDocument();

    // CurriculumPanel stub is rendered
    expect(screen.getByTestId('curriculum-panel-stub')).toBeInTheDocument();

    // Scaffold heading must NOT be present for GB
    expect(screen.queryByText('2. Scaffold from GB')).not.toBeInTheDocument();
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

  it('shows a published-lesson badge and no per-level generate button (native batch only)', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 }],
      'us-mod': [{ id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 3 }],
    };
    render(<MarketContent />, { wrapper });
    // The US level has 3 published lessons — badge visible
    expect(await screen.findByText('3 published')).toBeInTheDocument();
    // The retired per-level from-GB button must not exist
    expect(screen.queryByRole('button', { name: /regenerate \(replace\)/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /generate lessons \(from gb\)/i })).not.toBeInTheDocument();
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

  it('opens inline draft review in place instead of navigating away', async () => {
    briefData = { market_code: 'US', brief_json: { currency: 'USD' }, status: 'verified', model_used: 'm' };
    modulesData = [
      { id: 'gb-mod', topic: 'saving', title: 'Saving', market_code: 'GB', order_index: 0 },
      { id: 'us-mod', topic: 'saving', title: 'Saving (US)', market_code: 'US', order_index: 0 },
    ];
    levelsByModule = {
      'gb-mod': [{ id: 'gb-lvl', module_id: 'gb-mod', title: 'Basics', order_index: 0, lesson_count: 0 }],
      'us-mod': [
        // generated-but-not-approved: 5 drafts, 0 published lessons
        { id: 'us-lvl', module_id: 'us-mod', title: 'Basics (US)', order_index: 0, lesson_count: 0, draft_count: 5 },
      ],
    };
    render(<MarketContent />, { wrapper });

    // Should render a button (not a link) for reviewing drafts
    const btn = await screen.findByRole('button', { name: /review 5 draft/i });
    expect(btn).toBeInTheDocument();

    // No anchor navigating to /lessons should exist
    const lessonLinks = screen.queryAllByRole('link');
    const lessonsNav = lessonLinks.filter((el) =>
      el.getAttribute('href')?.includes('/lessons'),
    );
    expect(lessonsNav).toHaveLength(0);

    // Clicking the button reveals the inline review panel heading
    fireEvent.click(btn);
    expect(await screen.findByText('Review drafts')).toBeInTheDocument();
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
