import { describe, it, expect } from 'vitest';
import { isYouTubeMessage, YT_MESSAGE_TYPE } from '../useYouTubePlayer';

describe('isYouTubeMessage', () => {
  it('accepts the tagged ended/error/ready/playing shapes', () => {
    expect(isYouTubeMessage({ type: YT_MESSAGE_TYPE, event: 'ended' })).toBe(true);
    expect(isYouTubeMessage({ type: YT_MESSAGE_TYPE, event: 'error', code: 153 })).toBe(true);
    expect(isYouTubeMessage({ type: YT_MESSAGE_TYPE, event: 'ready' })).toBe(true);
    expect(isYouTubeMessage({ type: YT_MESSAGE_TYPE, event: 'playing' })).toBe(true);
  });

  it('rejects wrong type, wrong event, and non-object payloads', () => {
    expect(isYouTubeMessage({ type: 'something-else', event: 'ended' })).toBe(false);
    expect(isYouTubeMessage({ type: YT_MESSAGE_TYPE, event: 'exploded' })).toBe(false);
    expect(isYouTubeMessage({ event: 'ended' })).toBe(false);
    expect(isYouTubeMessage(null)).toBe(false);
    expect(isYouTubeMessage('investikid-yt')).toBe(false);
    expect(isYouTubeMessage(undefined)).toBe(false);
  });
});
