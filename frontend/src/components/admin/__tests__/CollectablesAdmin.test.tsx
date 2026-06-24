import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import CollectablesAdmin from '../CollectablesAdmin';

const scheduleMut = vi.fn().mockResolvedValue({});
const editMut = vi.fn().mockResolvedValue({});
const unscheduleMut = vi.fn().mockResolvedValue({});

const scheduledDrop = {
  item_id: 's1', slug: 'star', name: 'Star', emoji: '⭐', type: 'accessory',
  rarity: 'rare' as const, unlock_type: 'streak_days' as const, unlock_threshold: 5,
  available_from: '2026-08-01T00:00:00Z', available_until: '2026-08-08T00:00:00Z',
  status: 'scheduled' as const, owned_count: 0,
};

vi.mock('@/api/adminCollectables', async (orig) => {
  const actual = await (orig as () => Promise<Record<string, unknown>>)();
  return {
    ...actual,
    usePool: () => ({ data: [{ item_id: 'p1', slug: 'crown', name: 'Crown', emoji: '👑', type: 'accessory' }] }),
    useDrops: () => ({ data: [
      { item_id: 'd1', slug: 'hat', name: 'Hat', emoji: '🎩', type: 'accessory', rarity: 'rare',
        unlock_type: 'streak_days', unlock_threshold: 7, available_from: '2026-07-01T00:00:00Z',
        available_until: '2026-07-31T00:00:00Z', status: 'live', owned_count: 3 },
      scheduledDrop,
    ] }),
    useScheduleDrop: () => ({ mutateAsync: scheduleMut, isPending: false }),
    useEditDrop: () => ({ mutateAsync: editMut, isPending: false }),
    useUnscheduleDrop: () => ({ mutateAsync: unscheduleMut, isPending: false }),
  };
});

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.count != null ? `${k}:${o.count}` : k) }),
}));

describe('CollectablesAdmin', () => {
  beforeEach(() => { scheduleMut.mockClear(); editMut.mockClear(); unscheduleMut.mockClear(); });

  it('lists a live drop with its owned count', () => {
    render(<CollectablesAdmin />);
    expect(screen.getByText('Hat')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('schedules a drop from the pool', async () => {
    render(<CollectablesAdmin />);
    fireEvent.change(screen.getByDisplayValue('—'), { target: { value: 'p1' } });
    const dts = document.querySelectorAll('input[type="datetime-local"]');
    fireEvent.change(dts[0], { target: { value: '2026-08-01T00:00' } });
    fireEvent.change(dts[1], { target: { value: '2026-08-08T00:00' } });
    fireEvent.click(screen.getByText('collectables.save'));
    await waitFor(() => expect(scheduleMut).toHaveBeenCalledTimes(1));
    expect(scheduleMut.mock.calls[0][0].item_id).toBe('p1');
  });

  it('edits a scheduled drop', async () => {
    render(<CollectablesAdmin />);
    // Click Edit on the scheduled row
    fireEvent.click(screen.getByText('collectables.edit'));
    // Form should switch to edit mode
    expect(screen.getByText('collectables.editHeading')).toBeInTheDocument();
    // Submit the form in edit mode
    fireEvent.click(screen.getByText('collectables.save'));
    await waitFor(() => expect(editMut).toHaveBeenCalledTimes(1));
    const call = editMut.mock.calls[0][0] as { itemId: string; body: { unlock_threshold: number; rarity: string } };
    expect(call.itemId).toBe(scheduledDrop.item_id);
    expect(call.body.unlock_threshold).toBe(scheduledDrop.unlock_threshold);
    expect(call.body.rarity).toBe(scheduledDrop.rarity);
  });

  it('has no axe violations', async () => {
    const { container } = render(<CollectablesAdmin />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
