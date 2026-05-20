import { it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomTabBar } from '@/components/child/BottomTabBar';

it('every tab target sits inside the h-16 nav (≥44px tall)', () => {
  render(
    <MemoryRouter>
      <BottomTabBar />
    </MemoryRouter>,
  );
  // jsdom doesn't compute real layout; assert the container chain implies
  // adequate size. Real-world layout is validated by the Playwright e2e
  // axe scan (Task 3).
  for (const link of screen.getAllByRole('link')) {
    // The `h-16` container is the inner flex row inside `<nav>`.
    const row = link.closest('div.h-16, [class*="h-16"]');
    expect(row, 'expected link to be inside an h-16 row').not.toBeNull();
  }
});
