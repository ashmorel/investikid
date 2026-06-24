import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import Arcade from '../Arcade';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Arcade hub', () => {
  it('lists Quiz Rush with a play link', () => {
    wrap(<Arcade />);
    expect(screen.getByRole('link', { name: /quiz rush/i })).toHaveAttribute('href', '/arcade/quiz-rush');
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<Arcade />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
