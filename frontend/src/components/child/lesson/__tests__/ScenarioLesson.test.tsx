import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { ScenarioLesson } from '../ScenarioLesson';

const content = {
  prompt: 'You receive £20 for your birthday. What do you do?',
  choices: [
    { label: 'Save it all', outcome: 'Great choice! Saving helps you reach goals.' },
    { label: 'Spend it all immediately', outcome: 'Spending it all means nothing left for later.' },
    { label: 'Share some with a friend', outcome: 'Generous, but saving some first is wise.' },
  ],
  correct_index: 0,
};

describe('ScenarioLesson', () => {
  it('renders the scenario eyebrow, prompt, and choices', () => {
    render(<ScenarioLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.getByText(/Real-life scenario/)).toBeInTheDocument();
    expect(screen.getByText(/You receive £20/)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Save it all/ })).toBeInTheDocument();
  });

  it('correct answer: select → Check answer → Correct! → Continue calls onComplete(1)', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<ScenarioLesson contentJson={content} onComplete={onComplete} />);

    await user.click(screen.getByRole('radio', { name: /Save it all/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(screen.getByText('Correct!')).toBeInTheDocument();
    expect(screen.getByText(/Great choice!/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onComplete).toHaveBeenCalledWith(1);
  });

  it('wrong answer: shows Not quite! with the chosen outcome, onComplete called with 0', async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<ScenarioLesson contentJson={content} onComplete={onComplete} />);

    await user.click(screen.getByRole('radio', { name: /Spend it all immediately/ }));
    await user.click(screen.getByRole('button', { name: /Check answer/i }));

    expect(screen.getByText('Not quite!')).toBeInTheDocument();
    expect(screen.getByText(/nothing left for later/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Continue/i }));
    expect(onComplete).toHaveBeenCalledWith(0);
  });

  it('Check answer disabled until a choice is selected', () => {
    render(<ScenarioLesson contentJson={content} onComplete={() => {}} />);
    expect(screen.getByRole('button', { name: /Check answer/i })).toBeDisabled();
  });

  it('renders Ask Coach Penny when onShowPenny provided', async () => {
    const user = userEvent.setup();
    const onShowPenny = vi.fn();
    render(<ScenarioLesson contentJson={content} onComplete={() => {}} onShowPenny={onShowPenny} />);
    await user.click(screen.getByRole('button', { name: /Ask Coach Penny/i }));
    expect(onShowPenny).toHaveBeenCalled();
  });

  it('no a11y violations in the radiogroup', async () => {
    const { container } = render(<ScenarioLesson contentJson={content} onComplete={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
