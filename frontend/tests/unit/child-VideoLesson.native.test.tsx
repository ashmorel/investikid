import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';

vi.mock('@/lib/platform', () => ({
  isNativeApp: () => true,
}));

describe('VideoLesson on native', () => {
  it('shows a YouTube thumbnail link instead of an iframe', () => {
    const { container } = render(<VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />);

    expect(container.querySelector('iframe')).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: /lesson video thumbnail/i })).toHaveAttribute(
      'src',
      'https://img.youtube.com/vi/abc123/hqdefault.jpg',
    );
    expect(screen.getByRole('link', { name: /open lesson video on youtube/i })).toHaveAttribute(
      'href',
      'https://www.youtube.com/watch?v=abc123',
    );
  });
});
