import { render, screen, act, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { axe } from 'vitest-axe';
import { VideoLesson } from '../VideoLesson';

const YOUTUBE_ID = 'dQw4w9WgXcQ';
// The web embed plays from the nocookie origin; that's the origin postMessage
// events legitimately arrive from on web/Android.
const EMBED_ORIGIN = 'https://www.youtube-nocookie.com';
// iOS proxies YouTube events through the app shell, so they arrive with the app
// web origin (defaultWebOrigin() / youtubeMessageOrigins()) rather than the
// nocookie embed origin.
const APP_WEB_ORIGIN = 'https://app.investikid.ai';

const youtubeContent = {
  video_source: 'youtube' as const,
  youtube_id: YOUTUBE_ID,
  caption: 'A short lesson video',
  transcript: 'Saving means keeping money for later.',
  captions_available: true,
};

function postYt(event: 'ended' | 'error', opts: { origin?: string; type?: string; code?: number } = {}) {
  const ev = new MessageEvent('message', {
    data: { type: opts.type ?? 'investikid-yt', event, code: opts.code },
    origin: opts.origin ?? EMBED_ORIGIN,
  });
  act(() => {
    window.dispatchEvent(ev);
  });
}

describe('VideoLesson — IFrame Player API end-screen control + graceful failure', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    if (vi.isFakeTimers()) vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('ended event shows Mark complete panel, hides the iframe, auto-ticks watched, and onComplete fires', () => {
    const onComplete = vi.fn();
    render(<VideoLesson contentJson={youtubeContent} onComplete={onComplete} />);

    // Playing: the iframe is present.
    expect(document.querySelector('iframe[title="Lesson video"]')).toBeInTheDocument();

    postYt('ended');

    // Player hidden, finished panel visible.
    expect(document.querySelector('iframe[title="Lesson video"]')).not.toBeInTheDocument();
    expect(screen.getByText(/Finished/i)).toBeInTheDocument();
    const markComplete = screen.getByRole('button', { name: /Mark complete/i });
    expect(markComplete).toBeEnabled();

    fireEvent.click(markComplete);
    expect(onComplete).toHaveBeenCalledWith(null);
  });

  it('accepts an ended event from the app web origin (iOS proxy) and shows Mark complete', () => {
    const onComplete = vi.fn();
    render(<VideoLesson contentJson={youtubeContent} onComplete={onComplete} />);

    expect(document.querySelector('iframe[title="Lesson video"]')).toBeInTheDocument();

    // iOS proxies the IFrame Player event through the app shell, so it arrives
    // with the app web origin instead of the nocookie embed origin.
    postYt('ended', { origin: APP_WEB_ORIGIN });

    expect(document.querySelector('iframe[title="Lesson video"]')).not.toBeInTheDocument();
    expect(screen.getByText(/Finished/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark complete/i })).toBeEnabled();
  });

  it('error event (code 153) shows the friendly fallback + Continue calls onComplete(null)', () => {
    const onComplete = vi.fn();
    render(<VideoLesson contentJson={youtubeContent} onComplete={onComplete} />);

    postYt('error', { code: 153 });

    expect(screen.getByText(/taking a break/i)).toBeInTheDocument();
    // Transcript still available in the fallback.
    expect(screen.getByText(/Show transcript/i)).toBeInTheDocument();
    expect(document.querySelector('iframe[title="Lesson video"]')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onComplete).toHaveBeenCalledWith(null);
  });

  it('ready-timeout (8s, no ready/playing) shows the friendly fallback', () => {
    render(<VideoLesson contentJson={youtubeContent} onComplete={vi.fn()} />);

    expect(screen.queryByText(/taking a break/i)).not.toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(8000);
    });
    expect(screen.getByText(/taking a break/i)).toBeInTheDocument();
  });

  it('ignores a message with the wrong type (still playing)', () => {
    render(<VideoLesson contentJson={youtubeContent} onComplete={vi.fn()} />);
    postYt('ended', { type: 'evil-yt' });
    expect(document.querySelector('iframe[title="Lesson video"]')).toBeInTheDocument();
    expect(screen.queryByText(/Finished/i)).not.toBeInTheDocument();
  });

  it('ignores a message from an unexpected origin (still playing)', () => {
    render(<VideoLesson contentJson={youtubeContent} onComplete={vi.fn()} />);
    postYt('ended', { origin: 'https://evil.example.com' });
    expect(document.querySelector('iframe[title="Lesson video"]')).toBeInTheDocument();
    expect(screen.queryByText(/Finished/i)).not.toBeInTheDocument();
  });

  it('malformed id falls back to the existing Video unavailable path (unchanged)', () => {
    const onComplete = vi.fn();
    render(
      <VideoLesson
        contentJson={{ video_source: 'youtube', youtube_id: 'bad id!' }}
        onComplete={onComplete}
      />,
    );
    expect(screen.getByText(/Video unavailable/i)).toBeInTheDocument();
  });

  it('hosted video path renders a <video> element (unchanged)', () => {
    render(
      <VideoLesson
        contentJson={{ video_source: 'hosted', video_url: 'https://cdn.example.com/v.mp4' }}
        onComplete={vi.fn()}
      />,
    );
    expect(document.querySelector('video')).toBeInTheDocument();
    expect(document.querySelector('iframe[title="Lesson video"]')).not.toBeInTheDocument();
  });

  // axe needs real timers and cannot recurse into the live <iframe> under jsdom,
  // so the a11y checks run on the ended + fallback states (no iframe) separately.
  describe('a11y', () => {
    beforeEach(() => {
      vi.useRealTimers();
    });

    it('no a11y violations in the ended (Mark complete) state', async () => {
      const { container } = render(<VideoLesson contentJson={youtubeContent} onComplete={vi.fn()} />);
      act(() => {
        window.dispatchEvent(
          new MessageEvent('message', {
            data: { type: 'investikid-yt', event: 'ended' },
            origin: EMBED_ORIGIN,
          }),
        );
      });
      expect(screen.getByText(/Finished/i)).toBeInTheDocument();
      expect(await axe(container)).toHaveNoViolations();
    });

    it('no a11y violations in the friendly fallback state', async () => {
      const { container } = render(<VideoLesson contentJson={youtubeContent} onComplete={vi.fn()} />);
      act(() => {
        window.dispatchEvent(
          new MessageEvent('message', {
            data: { type: 'investikid-yt', event: 'error', code: 100 },
            origin: EMBED_ORIGIN,
          }),
        );
      });
      expect(screen.getByText(/taking a break/i)).toBeInTheDocument();
      expect(await axe(container)).toHaveNoViolations();
    });

    it('no a11y violations in the malformed-id fallback state', async () => {
      const { container } = render(
        <VideoLesson contentJson={{ video_source: 'youtube', youtube_id: 'bad id!' }} onComplete={vi.fn()} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});
