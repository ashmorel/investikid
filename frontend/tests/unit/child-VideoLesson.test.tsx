import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';
import { buildYouTubeUrls } from '@/components/child/lesson/videoEmbed';

describe('VideoLesson', () => {
  it('renders the nocookie iframe inline on the web build', () => {
    const { container } = render(<VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />);
    const iframe = container.querySelector('iframe')!;
    expect(iframe.src).toContain('youtube-nocookie.com/embed/abc123');
    expect(iframe.src).toContain('playsinline=1');
    expect(iframe).toHaveAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    expect(screen.getByRole('link', { name: /open video on youtube/i })).toHaveAttribute(
      'href',
      'https://www.youtube.com/watch?v=abc123',
    );
  });

  it('routes native (Capacitor) embeds through the https proxy page (fixes iOS error 153)', () => {
    const urls = buildYouTubeUrls('abc123', { isNative: true })!;

    expect(urls.embed).toBe('https://app.investikid.ai/yt.html?v=abc123');
    expect(urls.thumbnail).toBe('https://img.youtube.com/vi/abc123/hqdefault.jpg');
    expect(urls.watch).toBe('https://www.youtube.com/watch?v=abc123');
  });

  it('Mark complete is disabled until checkbox checked, then onComplete(null)', () => {
    const onComplete = vi.fn();
    render(<VideoLesson contentJson={{ youtube_id: 'abc' }} onComplete={onComplete} />);
    const button = screen.getByRole('button', { name: /Mark complete/ });
    expect(button).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/I watched this/));
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(onComplete).toHaveBeenCalledWith(null);
  });

  it('renders fallback when youtube_id missing and lets user complete', () => {
    const onComplete = vi.fn();
    render(<VideoLesson contentJson={{}} onComplete={onComplete} />);
    expect(screen.getByText(/Video unavailable/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onComplete).toHaveBeenCalledWith(null);
  });

  it('renders fallback for malformed youtube_id values', () => {
    render(<VideoLesson contentJson={{ youtube_id: '../bad?id=1' }} onComplete={() => {}} />);
    expect(screen.getByText(/Video unavailable/i)).toBeInTheDocument();
    expect(screen.queryByTitle(/lesson video/i)).not.toBeInTheDocument();
  });

  it('renders captions indicator and a disclosure for transcript', async () => {
    const u = userEvent.setup();
    render(
      <VideoLesson
        contentJson={{ youtube_id: 'abc', captions_available: true, transcript: 'Hello world transcript content.' }}
        onComplete={() => {}}
      />,
    );
    expect(screen.getByText(/Captions available/)).toBeInTheDocument();
    const trigger = screen.getByRole('button', { name: /show transcript/i });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await u.click(trigger);
    expect(screen.getByText('Hello world transcript content.')).toBeVisible();
  });

  it('shows "No captions" when flag is false and omits transcript when missing', () => {
    render(<VideoLesson contentJson={{ youtube_id: 'abc', captions_available: false }} onComplete={() => {}} />);
    expect(screen.getByText(/No captions/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /show transcript/i })).not.toBeInTheDocument();
  });

  it('renders an HTML5 <video> for a hosted source', () => {
    const { container } = render(
      <VideoLesson
        contentJson={{ video_source: 'hosted', video_url: 'https://cdn/videos/x.mp4', caption: 'c' }}
        onComplete={() => {}}
      />,
    );
    const video = container.querySelector('video');
    expect(video).not.toBeNull();
    expect(video).toHaveAttribute('src', 'https://cdn/videos/x.mp4');
    expect(video).toHaveAttribute('playsinline');
    // no YouTube iframe in hosted mode
    expect(container.querySelector('iframe')).toBeNull();
  });

  it('still renders the YouTube iframe when source is youtube (default)', () => {
    const { container } = render(<VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />);
    expect(container.querySelector('iframe')).not.toBeNull();
  });

  it('has no axe violations (fallback branch — no iframe)', async () => {
    // The YouTube iframe trips jsdom's window-postMessage in axe-core's frame
    // rules; layout-dependent frame checks are covered by the Playwright e2e
    // axe scan (Task 3). Here we exercise the no-iframe fallback branch, which
    // still validates Disclosure/Button/labelling axe-cleanness around it.
    const { container } = render(
      <VideoLesson contentJson={{}} onComplete={() => {}} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
