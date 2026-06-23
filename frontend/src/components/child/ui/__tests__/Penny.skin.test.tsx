import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Penny } from '../Penny';

describe('Penny skin prop', () => {
  it('applies sky skin gradient stops', () => {
    const { container } = render(<Penny skin="skin_sky" />);
    const stops = container.querySelectorAll('stop');
    const colours = Array.from(stops).map(
      (s) => s.getAttribute('stopColor') ?? s.getAttribute('stop-color') ?? '',
    );
    expect(colours).toContain('#38bdf8');
    expect(colours).toContain('#2563eb');
  });

  it('applies pink skin gradient stops (distinct from any mood gradient)', () => {
    const { container } = render(<Penny skin="skin_pink" />);
    const stops = container.querySelectorAll('stop');
    const colours = Array.from(stops).map(
      (s) => s.getAttribute('stopColor') ?? s.getAttribute('stop-color') ?? '',
    );
    expect(colours).toContain('#f9a8d4');
    expect(colours).toContain('#db2777');
  });

  it('keeps excited expression when skin is set', () => {
    const { container } = render(<Penny skin="skin_sky" mood="excited" />);
    // Excited eyes are ★ text elements
    const texts = container.querySelectorAll('text');
    const stars = Array.from(texts).filter((t) => t.textContent?.includes('★'));
    expect(stars.length).toBeGreaterThanOrEqual(2);
  });

  it('falls back to mood gradient when no skin is given', () => {
    const { container } = render(<Penny />);
    const stops = container.querySelectorAll('stop');
    const colours = Array.from(stops).map(
      (s) => s.getAttribute('stopColor') ?? s.getAttribute('stop-color') ?? '',
    );
    // happy mood = sky-400 → blue-600
    expect(colours).toContain('#38bdf8');
    expect(colours).toContain('#2563eb');
  });
});
