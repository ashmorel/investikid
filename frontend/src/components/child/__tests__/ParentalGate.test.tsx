import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
import { ParentalGate } from '../ParentalGate';

// With rng = () => 0.5: a = 3 + floor(3.5) = 6, b = 6, answer = 36.
const rng = () => 0.5;

describe('ParentalGate', () => {
  it('calls onPass only with the correct answer on continue', () => {
    const onPass = vi.fn();
    const onCancel = vi.fn();
    render(<ParentalGate onPass={onPass} onCancel={onCancel} rng={rng} />);

    fireEvent.change(screen.getByLabelText('parentalGate.answerLabel'), { target: { value: '36' } });
    fireEvent.click(screen.getByText('parentalGate.continue'));

    expect(onPass).toHaveBeenCalledTimes(1);
  });

  it('shows an error and does not call onPass on a wrong answer', () => {
    const onPass = vi.fn();
    const onCancel = vi.fn();
    render(<ParentalGate onPass={onPass} onCancel={onCancel} rng={rng} />);

    fireEvent.change(screen.getByLabelText('parentalGate.answerLabel'), { target: { value: '10' } });
    fireEvent.click(screen.getByText('parentalGate.continue'));

    expect(onPass).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('parentalGate.tryAgain');
  });

  it('calls onCancel when cancel is clicked', () => {
    const onPass = vi.fn();
    const onCancel = vi.fn();
    render(<ParentalGate onPass={onPass} onCancel={onCancel} rng={rng} />);

    fireEvent.click(screen.getByText('parentalGate.cancel'));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onPass).not.toHaveBeenCalled();
  });

  it('a11y clean', async () => {
    const { container } = render(
      <ParentalGate onPass={vi.fn()} onCancel={vi.fn()} rng={rng} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
