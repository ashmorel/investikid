import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { Button } from '@/components/ui/button';

describe('a11y smoke', () => {
  it('Button has no violations', async () => {
    const { container } = render(<Button>OK</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
