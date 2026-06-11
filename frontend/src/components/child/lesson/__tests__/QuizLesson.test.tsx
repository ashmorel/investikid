import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { QuizLesson } from '../QuizLesson';
import { playSound } from '@/lib/sound';
import { haptic } from '@/lib/haptics';

vi.mock('@/lib/sound', () => ({ playSound: vi.fn() }));
vi.mock('@/lib/haptics', () => ({ haptic: vi.fn() }));

const content = {
  question: 'What is 2 + 2?',
  choices: ['3', '4', '5', '6'],
  answer_index: 1,
  explanation: 'Two plus two equals four.',
};

describe('QuizLesson', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('correct answer fires the correct sound and success haptic exactly once', async () => {
    const user = userEvent.setup();
    render(<QuizLesson contentJson={content} onComplete={() => {}} />);

    await user.click(screen.getByRole('radio', { name: /^4$/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(playSound).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledWith('correct');
    expect(haptic).toHaveBeenCalledTimes(1);
    expect(haptic).toHaveBeenCalledWith('success');
  });

  it('wrong answer fires the wrong sound and warning haptic exactly once', async () => {
    const user = userEvent.setup();
    render(<QuizLesson contentJson={content} onComplete={() => {}} />);

    await user.click(screen.getByRole('radio', { name: /^3$/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(playSound).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledWith('wrong');
    expect(haptic).toHaveBeenCalledTimes(1);
    expect(haptic).toHaveBeenCalledWith('warning');
  });

  it('no a11y violations in the submitted feedback state', async () => {
    const user = userEvent.setup();
    const { container } = render(<QuizLesson contentJson={content} onComplete={() => {}} />);
    await user.click(screen.getByRole('radio', { name: /^3$/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders the question and choices', () => {
    render(<QuizLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.getByText('What is 2 + 2?')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /4/ })).toBeInTheDocument();
  });

  it('correct answer: select → Check answer → Correct! shown → Continue calls onComplete(1)', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<QuizLesson contentJson={content} onComplete={onComplete} />);

    await user.click(screen.getByRole('radio', { name: /^4$/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(screen.getByText('Correct!')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Check answer/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onComplete).toHaveBeenCalledWith(1);
  });

  it('wrong answer: onComplete called with 0', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<QuizLesson contentJson={content} onComplete={onComplete} />);

    await user.click(screen.getByRole('radio', { name: /^3$/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(screen.getByText('Not quite!')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onComplete).toHaveBeenCalledWith(0);
  });

  it('Check answer disabled until a choice is selected', () => {
    render(<QuizLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.getByRole('button', { name: /Check answer/i })).toBeDisabled();
  });

  it('renders Ask Coach Penny button when onShowPenny provided', async () => {
    const user = userEvent.setup();
    const onShowPenny = vi.fn();
    render(<QuizLesson contentJson={content} onComplete={() => {}} onShowPenny={onShowPenny} />);
    const btn = screen.getByRole('button', { name: /Ask Coach Penny/i });
    await user.click(btn);
    expect(onShowPenny).toHaveBeenCalled();
  });

  it('no a11y violations in the radiogroup', async () => {
    const { container } = render(<QuizLesson contentJson={content} onComplete={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
