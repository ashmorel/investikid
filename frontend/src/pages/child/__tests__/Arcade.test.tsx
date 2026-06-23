import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import Arcade from '../Arcade';

describe('Arcade hub', () => {
  it('lists Quiz Rush with a play link', () => {
    render(<MemoryRouter><Arcade /></MemoryRouter>);
    expect(screen.getByRole('link', { name: /quiz rush/i })).toHaveAttribute('href', '/arcade/quiz-rush');
  });

  it('has no axe violations', async () => {
    const { container } = render(<MemoryRouter><Arcade /></MemoryRouter>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
