import { describe, it, expect } from 'vitest';
import { buildYouTubeUrls } from '../videoEmbed';

const ID = 'dQw4w9WgXcQ';
const DEFAULT_WEB_ORIGIN = 'https://app.investikid.ai';

describe('buildYouTubeUrls', () => {
  it('returns null for an invalid id', () => {
    expect(buildYouTubeUrls('bad id!', { isNative: false })).toBeNull();
    expect(buildYouTubeUrls('   ', { isNative: true })).toBeNull();
  });

  it('web build embeds the nocookie player directly', () => {
    const urls = buildYouTubeUrls(ID, { isNative: false });
    expect(urls).not.toBeNull();
    expect(urls!.embed).toContain('https://www.youtube-nocookie.com/embed/' + ID);
    expect(urls!.embed).toContain('playsinline=1');
  });

  it('native build routes through the https proxy page (fixes iOS error 153)', () => {
    const urls = buildYouTubeUrls(ID, { isNative: true });
    expect(urls).not.toBeNull();
    expect(urls!.embed).toBe(`${DEFAULT_WEB_ORIGIN}/yt.html?v=${ID}`);
  });

  it('android native build embeds the nocookie player directly (no proxy)', () => {
    const urls = buildYouTubeUrls(ID, { isNative: true, isAndroid: true });
    expect(urls).not.toBeNull();
    expect(urls!.embed).toContain('https://www.youtube-nocookie.com/embed/' + ID);
    expect(urls!.embed).toContain('playsinline=1');
    expect(urls!.embed).not.toContain('/yt.html');
  });

  it('native proxy origin is overridable via VITE_WEB_ORIGIN', () => {
    const urls = buildYouTubeUrls(ID, { isNative: true, webOrigin: 'https://app.example.com' });
    expect(urls!.embed).toBe(`https://app.example.com/yt.html?v=${ID}`);
  });

  it('keeps thumbnail + watch links pointing at YouTube', () => {
    const urls = buildYouTubeUrls(ID, { isNative: true });
    expect(urls!.thumbnail).toBe(`https://img.youtube.com/vi/${ID}/hqdefault.jpg`);
    expect(urls!.watch).toBe(`https://www.youtube.com/watch?v=${ID}`);
  });
});
