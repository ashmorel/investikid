import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
import { MachineTranslatedBadge } from '../MachineTranslatedBadge';

describe('MachineTranslatedBadge', () => {
  it('renders the label', () => {
    render(<MachineTranslatedBadge />);
    expect(screen.getByText(/machineTranslated/i)).toBeInTheDocument();
  });

  it('a11y clean', async () => {
    const { container } = render(<MachineTranslatedBadge />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
