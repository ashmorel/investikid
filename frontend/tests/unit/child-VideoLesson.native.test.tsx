import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { VideoLesson } from '@/components/child/lesson/VideoLesson';

vi.mock('@/lib/platform', () => ({
  isNativeApp: () => true,
  isAndroid: () => false,
}));

describe('VideoLesson on native', () => {
  it('shows an inline iframe player on native', () => {
    const { container } = render(<VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />);

    const iframe = container.querySelector('iframe');
    expect(iframe).toBeInTheDocument();
    expect(iframe!.src).toContain('abc123');
  });
});
