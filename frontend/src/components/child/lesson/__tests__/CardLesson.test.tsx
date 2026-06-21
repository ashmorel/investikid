import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { CardLesson } from '../CardLesson';

const content = { title: 'What is saving?', body: 'Saving means keeping money for later instead of spending it now.' };

describe('CardLesson', () => {
  it('renders title and body', () => {
    render(<CardLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.getByText('What is saving?')).toBeInTheDocument();
    expect(screen.getByText(/Saving means keeping money/)).toBeInTheDocument();
  });

  it('Got it button calls onComplete with null', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<CardLesson contentJson={content} onComplete={onComplete} />);
    await user.click(screen.getByRole('button', { name: /Got it/i }));
    expect(onComplete).toHaveBeenCalledWith(null);
  });

  it('shows Saving… and disables button when completing=true', () => {
    render(<CardLesson contentJson={content} onComplete={() => {}} completing={true} />);
    const btn = screen.getByRole('button', { name: /Saving/i });
    expect(btn).toBeDisabled();
  });

  it('shows "Ask Coach Penny" and calls onShowPenny when provided', async () => {
    const user = userEvent.setup();
    const onShowPenny = vi.fn();
    render(<CardLesson contentJson={content} onComplete={() => {}} onShowPenny={onShowPenny} />);
    await user.click(screen.getByRole('button', { name: /ask coach penny/i }));
    expect(onShowPenny).toHaveBeenCalled();
  });

  it('hides "Ask Coach Penny" when onShowPenny is not provided', () => {
    render(<CardLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.queryByRole('button', { name: /ask coach penny/i })).not.toBeInTheDocument();
  });

  it('renders illustration when provided', () => {
    render(<CardLesson contentJson={content} onComplete={() => {}} illustration={<img src="test.png" alt="piggy bank" />} />);
    expect(screen.getByAltText('piggy bank')).toBeInTheDocument();
  });

  it('no a11y violations', async () => {
    const { container } = render(<CardLesson contentJson={content} onComplete={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
