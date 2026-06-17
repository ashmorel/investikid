import { describe, expect, it } from 'vitest';
import { pseudo } from '../../scripts/pseudo-transform.mjs';

describe('pseudo-locale transform', () => {
  it('accents and brackets a string so untranslated text is obvious', () => {
    const out = pseudo('Home');
    expect(out).not.toBe('Home');
    expect(out.startsWith('[')).toBe(true);
    // eslint-disable-next-line no-control-regex
    expect(out).toMatch(/[^\x00-\x7F]/); // contains non-ASCII accents
  });
  it('preserves interpolation placeholders', () => {
    expect(pseudo('You earned {{count}} XP')).toContain('{{count}}');
  });
});
