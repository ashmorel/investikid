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

  it('drives the nocookie player via the IFrame API with playsinline', () => {
    // Player is now built by the IFrame Player API against the nocookie host so
    // we can observe ended/error lifecycle events (no bare iframe end-screen).
    expect(html).toContain("host: 'https://www.youtube-nocookie.com'");
    expect(html).toContain('playsinline: 1');
    expect(html).toContain('https://www.youtube.com/iframe_api');
  });

  it('posts ended/error lifecycle events to the parent app', () => {
    expect(html).toContain("type: 'investikid-yt'");
    expect(html).toContain("notify('ended')");
    expect(html).toContain("notify('error'");
    expect(html).toContain('parent.postMessage');
  });

  it('declares a strict-origin referrer policy so YouTube gets a valid https referer', () => {
    expect(html).toContain('name="referrer"');
    expect(html).toContain('strict-origin-when-cross-origin');
  });

  it('validates the id before embedding (no arbitrary injection)', () => {
    expect(html).toContain('/^[A-Za-z0-9_-]+$/');
  });
});
