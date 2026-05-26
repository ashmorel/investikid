import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { EddieFAB } from '../EddieFAB';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate, useLocation: () => ({ pathname: '/home' }) };
});

describe('EddieFAB', () => {
  it('renders with accessible label', () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    expect(screen.getByRole('button', { name: /open coach eddie/i })).toBeInTheDocument();
  });

  it('shows badge dot when dueCount > 0', () => {
    render(<MemoryRouter><EddieFAB dueCount={3} /></MemoryRouter>);
    expect(screen.getByTestId('eddie-badge')).toBeInTheDocument();
  });

  it('hides badge dot when dueCount is 0', () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    expect(screen.queryByTestId('eddie-badge')).not.toBeInTheDocument();
  });

  it('navigates to /coach on click', async () => {
    render(<MemoryRouter><EddieFAB dueCount={0} /></MemoryRouter>);
    await userEvent.click(screen.getByRole('button', { name: /open coach eddie/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/coach');
  });
});
