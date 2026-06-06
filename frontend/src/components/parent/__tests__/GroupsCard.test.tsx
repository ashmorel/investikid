import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GroupsCard } from '../GroupsCard';

const toast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({ useToast: () => ({ toast }) }));

vi.mock('@/api/parent', () => ({
  parentApi: {
    listGroups: vi.fn(async () => [{ id: 'g1', name: 'Cousins', code: 'ABCD2345', is_owner: true, members: [{ child_user_id: 'c1', username: 'Sam' }] }]),
    createGroup: vi.fn(async () => ({ id: 'g2', name: 'New', code: 'WXYZ7890', is_owner: true, members: [] })),
    joinGroup: vi.fn(), removeGroupMember: vi.fn(), deleteGroup: vi.fn(),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe('GroupsCard', () => {
  it('lists groups with code + members', async () => {
    render(wrap(<GroupsCard childrenList={[{ user_id: 'c1', username: 'Sam' }]} />));
    expect(await screen.findByText('Cousins')).toBeInTheDocument();
    expect(screen.getByText(/ABCD2345/)).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<GroupsCard childrenList={[{ user_id: 'c1', username: 'Sam' }]} />));
    expect(await axe(container)).toHaveNoViolations();
  });
  it('shows an error toast when creating a group fails', async () => {
    toast.mockClear();
    const { parentApi } = await import('@/api/parent');
    (parentApi.createGroup as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('boom'));
    const user = userEvent.setup();
    render(wrap(<GroupsCard childrenList={[{ user_id: 'c1', username: 'Sam' }]} />));
    await user.type(screen.getByLabelText(/new group name/i), 'New Group');
    await user.click(screen.getByRole('button', { name: /create group/i }));
    await vi.waitFor(() => expect(toast).toHaveBeenCalled());
  });
});
