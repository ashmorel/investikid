import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { QuizLesson } from '../QuizLesson';

const content = {
  question: 'What is 2 + 2?',
  choices: ['3', '4', '5', '6'],
  answer_index: 1,
  explanation: 'Two plus two equals four.',
};

describe('QuizLesson', () => {
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

  it('renders Ask Coach Eddie button when onShowEddie provided', async () => {
    const user = userEvent.setup();
    const onShowEddie = vi.fn();
    render(<QuizLesson contentJson={content} onComplete={() => {}} onShowEddie={onShowEddie} />);
    const btn = screen.getByRole('button', { name: /Ask Coach Eddie/i });
    await user.click(btn);
    expect(onShowEddie).toHaveBeenCalled();
  });

  it('no a11y violations in the radiogroup', async () => {
    const { container } = render(<QuizLesson contentJson={content} onComplete={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
