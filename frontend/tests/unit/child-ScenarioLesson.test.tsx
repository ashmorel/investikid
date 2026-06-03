import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ScenarioLesson } from '@/components/child/lesson/ScenarioLesson';

const scenario = {
  prompt: 'You deposit £100 at 5% for 10 years. How much?',
  choices: [
    { label: '£150', outcome: 'Simple interest only.' },
    { label: '£163', outcome: 'Correct! Compounding added £13.' },
    { label: '£200', outcome: 'Too high.' },
  ],
  correct_index: 1,
};

describe('ScenarioLesson', () => {
  it('Check answer disabled until selection; outcome shown after check', () => {
    render(<ScenarioLesson contentJson={scenario} onComplete={() => {}} />);
    const submit = screen.getByRole('button', { name: /Check answer/ });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole('radio', { name: '£163' }));
    fireEvent.click(submit);
    expect(screen.getByText(/Correct! Compounding added £13\./)).toBeInTheDocument();
  });

  it('correct pick → onComplete(1.0)', () => {
    const onComplete = vi.fn();
    render(<ScenarioLesson contentJson={scenario} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole('radio', { name: '£163' }));
    fireEvent.click(screen.getByRole('button', { name: /Check answer/ }));
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onComplete).toHaveBeenCalledWith(1.0);
  });

  it("wrong pick → onComplete(0.0) and shows that pick's outcome", () => {
    const onComplete = vi.fn();
    render(<ScenarioLesson contentJson={scenario} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole('radio', { name: '£150' }));
    fireEvent.click(screen.getByRole('button', { name: /Check answer/ }));
    expect(screen.getByText(/Simple interest only\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onComplete).toHaveBeenCalledWith(0.0);
  });
});
