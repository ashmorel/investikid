import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { RouteErrorBoundary } from '../RouteErrorBoundary';

function Boom(): React.ReactElement {
  throw new Error('kaboom');
}

describe('RouteErrorBoundary', () => {
  beforeEach(() => {
    // React logs the caught error to console.error; silence it for clean output.
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders children when they do not throw', () => {
    render(
      <RouteErrorBoundary>
        <p>safe content</p>
      </RouteErrorBoundary>,
    );
    expect(screen.getByText('safe content')).toBeInTheDocument();
  });

  it('shows the recoverable fallback (not a blank screen) when a child throws', () => {
    render(
      <RouteErrorBoundary>
        <Boom />
      </RouteErrorBoundary>,
    );
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reload/i })).toBeInTheDocument();
  });

  it('fallback has no axe violations', async () => {
    const { container } = render(
      <RouteErrorBoundary>
        <Boom />
      </RouteErrorBoundary>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
