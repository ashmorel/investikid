import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Guards the static proxy page that fixes iOS YouTube error 153. If a regression
// guts it, these assertions catch it (the page can't be exercised in jsdom easily).
describe('public/yt.html proxy page', () => {
  const html = readFileSync(resolve(__dirname, '../../../../../public/yt.html'), 'utf8');

  it('reads the video id from the ?v= query param', () => {
    expect(html).toContain("params.get('v')");
  });

  it('embeds the nocookie player inline with playsinline', () => {
    expect(html).toContain('https://www.youtube-nocookie.com/embed/');
    expect(html).toContain('playsinline=1');
  });

  it('declares a strict-origin referrer policy so YouTube gets a valid https referer', () => {
    expect(html).toContain('name="referrer"');
    expect(html).toContain('strict-origin-when-cross-origin');
  });

  it('validates the id before embedding (no arbitrary injection)', () => {
    expect(html).toContain('/^[A-Za-z0-9_-]+$/');
  });
});
