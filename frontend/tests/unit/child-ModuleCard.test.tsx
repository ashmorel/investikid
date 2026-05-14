import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ModuleCard } from '@/components/child/ModuleCard';

const baseModule = {
  id: 'mod-1', topic: 'stocks' as const, title: 'What is a Stock?',
  country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false,
};

describe('ModuleCard', () => {
  it('renders title, topic badge, and progress', () => {
    render(
      <MemoryRouter>
        <ModuleCard module={baseModule} completedCount={2} totalCount={3} onLockedClick={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/What is a Stock\?/i)).toBeInTheDocument();
    expect(screen.getByText(/2\s*\/\s*3 quests/i)).toBeInTheDocument();
  });

  it('renders locked state with lock icon and Premium copy', () => {
    render(
      <MemoryRouter>
        <ModuleCard module={{ ...baseModule, locked: true, is_premium: true }} completedCount={0} totalCount={3} onLockedClick={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/locked/i)).toBeInTheDocument();
  });

  it('locked card click calls onLockedClick instead of navigating', () => {
    const onLocked = vi.fn();
    render(
      <MemoryRouter>
        <ModuleCard module={{ ...baseModule, locked: true }} completedCount={0} totalCount={1} onLockedClick={onLocked} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onLocked).toHaveBeenCalledOnce();
  });

  it('accessible card renders as a link to the module page', () => {
    render(
      <MemoryRouter>
        <ModuleCard module={baseModule} completedCount={0} totalCount={1} onLockedClick={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link')).toHaveAttribute('href', '/lessons/mod-1');
  });
});
