import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomTabBar } from '../BottomTabBar';

function renderBar(initialPath = '/home') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <BottomTabBar />
    </MemoryRouter>,
  );
}

describe('BottomTabBar', () => {
  it('renders all five tab labels', () => {
    renderBar();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Quests')).toBeInTheDocument();
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('Simulator')).toBeInTheDocument();
    expect(screen.getByText('Stats')).toBeInTheDocument();
  });

  it('has correct routes for each tab', () => {
    renderBar();
    const links = screen.getAllByRole('link');
    const hrefs = links.map((l) => l.getAttribute('href'));
    expect(hrefs).toContain('/home');
    expect(hrefs).toContain('/lessons');
    expect(hrefs).toContain('/progress');
    expect(hrefs).toContain('/simulator');
    expect(hrefs).toContain('/stats');
  });

  it('renders nav with aria-label "Primary mobile"', () => {
    renderBar();
    expect(screen.getByRole('navigation', { name: 'Primary mobile' })).toBeInTheDocument();
  });
});
