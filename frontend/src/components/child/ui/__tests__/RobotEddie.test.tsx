import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'vitest-axe';
import { RobotEddie } from '../RobotEddie';

describe('RobotEddie', () => {
  it('renders an svg sized by the size prop, decorative by default', () => {
    const { container } = render(<RobotEddie size={64} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('width', '64');
    expect(svg).toHaveAttribute('height', '64');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });
  it('has no accessibility violations', async () => {
    const { container } = render(<div>Eddie <RobotEddie size={40} /></div>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
