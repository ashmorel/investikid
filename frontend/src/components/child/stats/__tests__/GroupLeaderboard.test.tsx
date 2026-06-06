import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { GroupLeaderboard } from '../GroupLeaderboard';

const boards = [{
  group_id: 'g1', group_name: 'Cousins',
  entries: [
    { username: 'Sam', xp_this_week: 30, is_me: true },
    { username: 'Alex', xp_this_week: 10, is_me: false },
  ],
}];

describe('GroupLeaderboard', () => {
  it('renders group name, members and highlights me', () => {
    render(<GroupLeaderboard boards={boards} />);
    expect(screen.getByText('Cousins')).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
    expect(screen.getByText('Alex')).toBeInTheDocument();
    expect(screen.getByText(/you/i)).toBeInTheDocument();
  });
  it('shows the prompt when there are no groups', () => {
    render(<GroupLeaderboard boards={[]} />);
    expect(screen.getByText(/ask a parent/i)).toBeInTheDocument();
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<GroupLeaderboard boards={boards} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
