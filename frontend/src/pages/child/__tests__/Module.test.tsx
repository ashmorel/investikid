import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Module from '../Module';
import { useAgeTier } from '@/lib/ageTier';
import { celebrate } from '@/lib/confetti';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

let reducedMotion = false;
vi.mock('framer-motion', async (importOriginal) => ({
  ...(await importOriginal<typeof import('framer-motion')>()),
  useReducedMotion: () => reducedMotion,
}));
vi.mock('@/lib/ageTier', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/ageTier')>()),
  useAgeTier: vi.fn(() => 'explorer'),
}));
vi.mock('@/lib/confetti', () => ({ celebrate: vi.fn() }));
vi.mock('@/lib/sound', () => ({ playSound: vi.fn() }));
vi.mock('@/lib/haptics', () => ({ haptic: vi.fn() }));
vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open: vi.fn() }) }));
vi.mock('@/components/child/LevelCard', () => ({ LevelCard: () => <div data-testid="level-card" /> }));

const MODULES = [{ id: 'm1', title: 'Money Basics', icon: '💰', order_index: 1 }];

function level(overrides = {}) {
  return {
    id: 'l1',
    title: 'Level 1',
    order_index: 1,
    state: 'completed',
    locked_reason: null,
    lessons_total: 3,
    lessons_completed: 3,
    ...overrides,
  };
}

const listModules = vi.fn();
const listLevels = vi.fn();
vi.mock('@/api/content', () => ({
  contentApi: {
    listModules: (...args: unknown[]) => listModules(...args),
    listLevels: (...args: unknown[]) => listLevels(...args),
  },
}));

const mockUseAgeTier = vi.mocked(useAgeTier);

function renderModule() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/lessons/m1']}>
        <Routes>
          <Route path="/lessons/:moduleId" element={<Module />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Module mastery celebration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reducedMotion = false;
    mockUseAgeTier.mockReturnValue('explorer');
    listModules.mockResolvedValue(MODULES);
    listLevels.mockResolvedValue([level()]);
  });

  it('explorer + all levels complete: confetti + mastery sound + heavy haptic, once', async () => {
    renderModule();
    expect(await screen.findByText(/Module complete!/)).toBeInTheDocument();
    expect(playSound).toHaveBeenCalledExactlyOnceWith('mastery');
    expect(haptic).toHaveBeenCalledExactlyOnceWith('heavy');
    expect(celebrate).toHaveBeenCalledTimes(1);
  });

  it('investor: mastery sound fires but confetti does not', async () => {
    mockUseAgeTier.mockReturnValue('investor');
    renderModule();
    expect(await screen.findByText(/Module complete\./)).toBeInTheDocument();
    expect(playSound).toHaveBeenCalledExactlyOnceWith('mastery');
    expect(celebrate).not.toHaveBeenCalled();
  });

  it('reduced motion: no confetti, sound still fires', async () => {
    reducedMotion = true;
    renderModule();
    expect(await screen.findByText(/Module complete!/)).toBeInTheDocument();
    expect(playSound).toHaveBeenCalledExactlyOnceWith('mastery');
    expect(celebrate).not.toHaveBeenCalled();
  });

  it('does not celebrate when levels remain incomplete', async () => {
    listLevels.mockResolvedValue([level(), level({ id: 'l2', order_index: 2, state: 'available', lessons_completed: 0 })]);
    renderModule();
    expect(await screen.findByText('Money Basics')).toBeInTheDocument();
    expect(playSound).not.toHaveBeenCalled();
    expect(celebrate).not.toHaveBeenCalled();
  });
});
