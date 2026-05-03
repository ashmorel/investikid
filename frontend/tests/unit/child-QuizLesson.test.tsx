import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QuizLesson } from '@/components/child/lesson/QuizLesson';

const quiz = {
  question: 'Q?',
  choices: ['A', 'B', 'C', 'D'],
  answer_index: 2,
  explanation: 'Because C.',
};

describe('QuizLesson', () => {
  it('Submit is disabled until a choice is selected', () => {
    render(<QuizLesson contentJson={quiz} onComplete={() => {}} />);
    const submit = screen.getByRole('button', { name: /Submit/ });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole('radio', { name: 'A' }));
    expect(submit).toBeEnabled();
  });

  it('submit reveals explanation and disables further selection', () => {
    render(<QuizLesson contentJson={quiz} onComplete={() => {}} />);
    fireEvent.click(screen.getByRole('radio', { name: 'A' }));
    fireEvent.click(screen.getByRole('button', { name: /Submit/ }));
    expect(screen.getByText(/Because C\./)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Submit/ })).not.toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'A' })).toBeDisabled();
  });

  it('correct pick → onComplete(1.0)', () => {
    const onComplete = vi.fn();
    render(<QuizLesson contentJson={quiz} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole('radio', { name: 'C' }));
    fireEvent.click(screen.getByRole('button', { name: /Submit/ }));
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onComplete).toHaveBeenCalledWith(1.0);
  });

  it('wrong pick → onComplete(0.0)', () => {
    const onComplete = vi.fn();
    render(<QuizLesson contentJson={quiz} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole('radio', { name: 'A' }));
    fireEvent.click(screen.getByRole('button', { name: /Submit/ }));
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onComplete).toHaveBeenCalledWith(0.0);
  });
});
