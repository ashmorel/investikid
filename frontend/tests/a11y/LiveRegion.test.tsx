import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { LiveRegion } from '@/components/a11y/LiveRegion';
import { useAnnounce } from '@/components/a11y/useAnnounce';

function Caller() {
  const announce = useAnnounce();
  return <button onClick={() => announce('Saved')}>save</button>;
}

describe('LiveRegion', () => {
  it('exposes a polite live region', () => {
    render(<LiveRegion><Caller /></LiveRegion>);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('announces messages from useAnnounce', async () => {
    render(<LiveRegion><Caller /></LiveRegion>);
    await act(async () => { screen.getByText('save').click(); });
    // The implementation uses a setTimeout(0) to force change-detection; flush it.
    await act(async () => { await new Promise(r => setTimeout(r, 1)); });
    expect(screen.getByRole('status')).toHaveTextContent('Saved');
  });
});
