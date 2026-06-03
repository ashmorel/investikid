import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { StatChip } from '../StatChip';
import { HeroCard } from '../HeroCard';
import { ModuleTile } from '../ModuleTile';
import { FeedbackPanel } from '../FeedbackPanel';

describe('ui primitives', () => {
  it('StatChip shows value + label', () => {
    render(<StatChip emoji="🔥" value="6" label="Streak" />);
    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText('Streak')).toBeInTheDocument();
  });
  it('HeroCard renders title + CTA link', () => {
    render(<MemoryRouter><HeroCard eyebrow="Up next" icon="📈" title="What is a Stock?" cta="Start" to="/x" /></MemoryRouter>);
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /start/i })).toHaveAttribute('href', '/x');
  });
  it('ModuleTile shows title and links when unlocked', () => {
    render(<MemoryRouter><ModuleTile emoji="📈" title="Stocks" subtitle="3 / 8" accent="#fbbf24" tint="#fff4d6" to="/m" /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /stocks/i })).toBeInTheDocument();
  });
  it('FeedbackPanel correct + incorrect render', () => {
    const { rerender } = render(<FeedbackPanel correct explanation="because" />);
    expect(screen.getByText(/correct!/i)).toBeInTheDocument();
    rerender(<FeedbackPanel correct={false} explanation="because" correctAnswer="£10" />);
    expect(screen.getByText(/not quite/i)).toBeInTheDocument();
  });
  it('no a11y violations', async () => {
    const { container } = render(<MemoryRouter>
      <StatChip emoji="⭐" value="120" label="XP" />
      <FeedbackPanel correct explanation="x" />
    </MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
