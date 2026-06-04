import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { Penny } from '../Penny';

describe('Penny', () => {
  it('renders a decorative svg sized by the size prop', () => {
    const { container } = render(<Penny size={64} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toBeTruthy();
    expect(svg.getAttribute('width')).toBe('64');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
  });

  it('gives each instance a unique gradient id', () => {
    const { container } = render(
      <>
        <Penny />
        <Penny />
      </>,
    );
    const ids = Array.from(container.querySelectorAll('linearGradient')).map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('renders star eyes only in the excited mood', () => {
    const { container: happy } = render(<Penny mood="happy" />);
    const { container: excited } = render(<Penny mood="excited" />);
    expect(happy.querySelectorAll('text').length).toBe(0);
    expect(excited.querySelectorAll('text').length).toBe(2);
  });

  it('has no axe violations', async () => {
    const { container } = render(<Penny />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
