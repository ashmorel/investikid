import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

let mockTier: 'explorer' | 'investor' = 'explorer';
vi.mock('@/lib/ageTier', async (importOriginal) => {
  const orig = await importOriginal<typeof import('@/lib/ageTier')>();
  return { ...orig, useAgeTier: () => mockTier };
});

import { QuickLinksRow } from '../QuickLinksRow';

const renderRow = (p = {}) =>
  render(
    <MemoryRouter>
      <QuickLinksRow portfolioValue="1240.50" currencyCode="USD" reviewDue={2} badgesEarned={7} badgesTotal={24} {...p} />
    </MemoryRouter>,
  );

describe('QuickLinksRow', () => {
  beforeEach(() => { mockTier = 'explorer'; });
  it('renders portfolio, review and badges chips with correct links', () => {
    renderRow();
    expect(screen.getByRole('link', { name: /portfolio/i })).toHaveAttribute('href', '/simulator');
    expect(screen.getByRole('link', { name: /2 to review/i })).toHaveAttribute('href', '/progress');
    expect(screen.getByRole('link', { name: /badges/i })).toHaveAttribute('href', '/stats');
    expect(screen.getByText(/\$1,240\.50/)).toBeInTheDocument();
    expect(screen.getByText(/7 of 24/)).toBeInTheDocument();
  });
  it('hides chips without data', () => {
    renderRow({ reviewDue: 0 });
    expect(screen.queryByRole('link', { name: /to review/i })).toBeNull();
  });
  it('hides the whole row when no chips have data', () => {
    const { container } = renderRow({ portfolioValue: null, reviewDue: 0, badgesEarned: null, badgesTotal: null });
    expect(container.querySelector('nav')).toBeNull();
  });
  it('investor tier renders without emoji', () => {
    mockTier = 'investor';
    const { container } = renderRow();
    expect(container.textContent).not.toMatch(/[📊🔁🏅]/u);
  });
  it('has no axe violations', async () => {
    expect(await axe(renderRow().container)).toHaveNoViolations();
  });
});
