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

  it('renders multiple stacked accessories at once, each in its own group', () => {
    const { container } = render(<Penny accessories={['crown', 'sunglasses']} />);
    expect(container.querySelector('[data-accessory="crown"]')).toBeTruthy();
    expect(container.querySelector('[data-accessory="sunglasses"]')).toBeTruthy();
  });

  it('renders a single accessory via the legacy `accessory` prop', () => {
    const { container } = render(<Penny accessory="crown" />);
    expect(container.querySelector('[data-accessory="crown"]')).toBeTruthy();
  });

  it('draws every accessory as flat SVG shapes, never emoji text', () => {
    // Accessories are hand-drawn SVG (professional, consistent), not emoji —
    // emoji <text> previously inherited fill="none" and was invisible anyway.
    const slugs = ['party_hat', 'sunglasses', 'bow', 'headphones', 'grad_cap', 'crown', 'monocle', 'top_hat'];
    const { container } = render(<Penny accessories={slugs} />);
    // No emoji text nodes at all.
    expect(container.querySelectorAll('text')).toHaveLength(0);
    // Each slug renders a group containing at least one drawn shape.
    for (const slug of slugs) {
      const g = container.querySelector(`[data-accessory="${slug}"]`);
      expect(g, `accessory ${slug} should render`).toBeTruthy();
      expect(g!.querySelector('polygon, rect, circle, ellipse, path, line')).toBeTruthy();
    }
  });

  it('renders nothing for an unknown accessory slug (forward-compatible)', () => {
    const { container } = render(<Penny accessories={['not_a_real_slug']} />);
    expect(container.querySelector('[data-accessory="not_a_real_slug"]')).toBeNull();
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
