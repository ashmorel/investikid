import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { PremiumBadge } from '@/components/child/PremiumBadge';

describe('a11y: PremiumBadge', () => {
  it('no axe violations', async () => {
    const { container } = render(<PremiumBadge />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
