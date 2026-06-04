import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { AuthPage } from '../AuthPage';

describe('AuthPage', () => {
  it('renders the wordmark, a single h1 title, subtitle, and children', () => {
    render(
      <AuthPage title="Welcome back!" subtitle="Let's keep learning.">
        <button>child</button>
      </AuthPage>,
    );

    expect(screen.getByText('InvestiKid')).toBeInTheDocument();
    const h1s = screen.getAllByRole('heading', { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent('Welcome back!');
    expect(screen.getByText("Let's keep learning.")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'child' })).toBeInTheDocument();
  });

  it('renders without a title (no h1) when title omitted', () => {
    render(
      <AuthPage>
        <p>hi</p>
      </AuthPage>,
    );

    expect(screen.queryByRole('heading', { level: 1 })).toBeNull();
  });

  it('has no axe violations', async () => {
    const { container } = render(
      <AuthPage title="Hi">
        <label htmlFor="x">Email</label>
        <input id="x" />
      </AuthPage>,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
