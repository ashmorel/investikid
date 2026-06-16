import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomTabBar } from '@/components/child/BottomTabBar';

describe('BottomTabBar', () => {
  it('renders six nav links', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(6);
  });

  it('highlights the active tab', () => {
    render(
      <MemoryRouter initialEntries={['/lessons']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    const learnLink = screen.getByRole('link', { name: /learn/i });
    expect(learnLink.className).toContain('text-brand-600');
  });

  it('shows correct labels for all tabs', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <BottomTabBar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Learn')).toBeInTheDocument();
    expect(screen.getByText('Revise')).toBeInTheDocument();
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('Simulator')).toBeInTheDocument();
    expect(screen.getByText('Stats')).toBeInTheDocument();
  });
});
