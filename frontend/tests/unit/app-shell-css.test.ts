import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('app shell CSS', () => {
  it('prevents horizontal document overflow in iOS WebView', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/index.css'), 'utf8');

    expect(css).toContain('html, body, #root');
    expect(css).toContain('max-width: 100%');
    expect(css).toContain('overflow-x: hidden');
  });
});
