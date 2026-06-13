import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { GroupChallenges } from '@/api/groups';
import { GroupGoals } from '../GroupGoals';

let blocks: GroupChallenges[];
vi.mock('@/api/groups', () => ({
  groupsApi: { myChallenges: () => Promise.resolve(blocks) },
}));
vi.mock('@/lib/ageTier', async (importOriginal) => {
  const orig = await importOriginal<typeof import('@/lib/ageTier')>();
  return { ...orig, useAgeTier: () => 'explorer' };
});

function renderGoals() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GroupGoals />
    </QueryClientProvider>,
  );
}

const challenge = {
  id: 'c1', title: 'Learn 20 lessons together', description: 'Teamwork!',
  target_value: 20, group_progress: 14, completed: false, ends_at: '2026-06-19T00:00:00Z',
};

describe('GroupGoals (m9)', () => {
  it('shows group progress bars', async () => {
    blocks = [{ group_id: 'g1', group_name: 'The Savers', challenges: [challenge] }];
    renderGoals();
    expect(await screen.findByText(/the savers — group goals/i)).toBeInTheDocument();
    expect(screen.getByText('14 / 20')).toBeInTheDocument();
    const bar = screen.getByRole('progressbar', { name: /learn 20 lessons together/i });
    expect(bar).toHaveAttribute('aria-valuenow', '14');
  });

  it('shows the completed state', async () => {
    blocks = [{ group_id: 'g1', group_name: 'The Savers', challenges: [{ ...challenge, group_progress: 20, completed: true }] }];
    renderGoals();
    expect(await screen.findByText(/completed! 🎉/i)).toBeInTheDocument();
  });

  it('renders nothing without active group challenges', async () => {
    blocks = [];
    const { container } = renderGoals();
    await waitFor(() => expect(container.querySelector('section')).toBeNull());
  });

  it('has no axe violations', async () => {
    blocks = [{ group_id: 'g1', group_name: 'The Savers', challenges: [challenge] }];
    const { container } = renderGoals();
    await screen.findByText(/group goals/i);
    expect(await axe(container)).toHaveNoViolations();
  });
});
