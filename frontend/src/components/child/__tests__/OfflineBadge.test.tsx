// frontend/src/components/child/__tests__/OfflineBadge.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { OfflineBadge } from '../OfflineBadge';
import { LevelCard } from '../LevelCard';
import type { LevelOut } from '@/api/content';

const baseLevel: LevelOut = {
  id: 'lv-1', module_id: 'm1', title: 'Level 1', order_index: 0, is_premium: false,
  icon: '📊', state: 'in_progress', locked_reason: null, passed: false,
  lessons_total: 3, lessons_completed: 1,
};

describe('OfflineBadge', () => {
  it('renders the "Available offline" label', () => {
    render(<OfflineBadge />);
    expect(screen.getByText(/available offline/i)).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<OfflineBadge />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('OfflineBadge mount in LevelCard', () => {
  it('shows the badge when isOfflineAvailable is true', () => {
    render(
      <LevelCard
        level={baseLevel}
        onOpen={() => {}}
        onLockedClick={() => {}}
        isOfflineAvailable={true}
      />,
    );
    expect(screen.getByText(/available offline/i)).toBeInTheDocument();
  });

  it('does not show the badge when isOfflineAvailable is false', () => {
    render(
      <LevelCard
        level={baseLevel}
        onOpen={() => {}}
        onLockedClick={() => {}}
        isOfflineAvailable={false}
      />,
    );
    expect(screen.queryByText(/available offline/i)).not.toBeInTheDocument();
  });

  it('does not show the badge when isOfflineAvailable is omitted', () => {
    render(
      <LevelCard
        level={baseLevel}
        onOpen={() => {}}
        onLockedClick={() => {}}
      />,
    );
    expect(screen.queryByText(/available offline/i)).not.toBeInTheDocument();
  });

  it('has no axe violations with badge shown', async () => {
    const { container } = render(
      <LevelCard
        level={baseLevel}
        onOpen={() => {}}
        onLockedClick={() => {}}
        isOfflineAvailable={true}
      />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
