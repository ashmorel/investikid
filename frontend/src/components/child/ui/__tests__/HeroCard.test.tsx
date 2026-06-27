import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { HeroCard } from '../HeroCard';

const renderCard = (variant?: 'playful' | 'flat') =>
  render(
    <MemoryRouter>
      <HeroCard eyebrow="Continue learning" icon="📈" title="What is a Stock?" subtitle="Level 2 · Lesson 3" cta="Continue" to="/lessons/1/2/3" variant={variant} />
    </MemoryRouter>,
  );

describe('HeroCard variants', () => {
  it('defaults to playful (gradient) and shows the icon', () => {
    const { container } = renderCard();
    expect(container.querySelector('.bg-brand-gradient')).not.toBeNull();
    expect(screen.getByText('📈')).toBeInTheDocument();
  });
  it('flat variant is a white bordered card without the emoji icon', () => {
    const { container } = renderCard('flat');
    expect(container.querySelector('.bg-brand-gradient')).toBeNull();
    expect(container.querySelector('.bg-white')).not.toBeNull();
    expect(screen.queryByText('📈')).toBeNull();
  });
  it('renders with CSS animation class and no framer-motion', () => {
    const { container } = renderCard();
    expect(container.querySelector('.animate-hero-card-in')).not.toBeNull();
  });
  it('has no axe violations in both variants', async () => {
    expect(await axe(renderCard().container)).toHaveNoViolations();
    expect(await axe(renderCard('flat').container)).toHaveNoViolations();
  });
});
