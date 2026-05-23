import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ReviewBanner } from '../ReviewBanner';

describe('ReviewBanner', () => {
  it('renders when due_count > 0', () => {
    render(<ReviewBanner dueCount={3} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/3 concepts/i)).toBeInTheDocument();
  });

  it('is hidden when due_count is 0', () => {
    const { container } = render(<ReviewBanner dueCount={0} />);
    expect(container.firstChild).toBeNull();
  });

  it('uses singular for 1 concept', () => {
    render(<ReviewBanner dueCount={1} />);
    expect(screen.getByText(/1 concept to/i)).toBeInTheDocument();
  });
});
