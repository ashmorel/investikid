import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CardLesson } from '@/components/child/lesson/CardLesson';

describe('CardLesson', () => {
  it('renders title and body and calls onComplete(null) on Got it click', () => {
    const onComplete = vi.fn();
    render(<CardLesson contentJson={{ title: 'A stock', body: 'Body text' }} onComplete={onComplete} />);
    expect(screen.getByRole('heading', { name: /A stock/ })).toBeInTheDocument();
    expect(screen.getByText(/Body text/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Got it/ }));
    expect(onComplete).toHaveBeenCalledWith(null);
  });
});
