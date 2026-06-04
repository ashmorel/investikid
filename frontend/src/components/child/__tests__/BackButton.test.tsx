import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { BackButton } from '../BackButton';

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('BackButton', () => {
  it('links to the target with an accessible name', () => {
    wrap(<BackButton to="/simulator" label="Simulator" />);
    const link = screen.getByRole('link', { name: /back to simulator/i });
    expect(link).toHaveAttribute('href', '/simulator');
    expect(link).toHaveTextContent('Simulator');
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<BackButton to="/lessons" label="Quests" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
