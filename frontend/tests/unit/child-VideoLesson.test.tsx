import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';

describe('VideoLesson', () => {
  it('renders nocookie iframe with given youtube_id', () => {
    const { container } = render(<VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />);
    const iframe = container.querySelector('iframe')!;
    expect(iframe.src).toContain('youtube-nocookie.com/embed/abc123');
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
});
