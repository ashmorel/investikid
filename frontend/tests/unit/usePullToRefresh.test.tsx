import { render, fireEvent, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRef } from 'react';
import { usePullToRefresh } from '@/hooks/usePullToRefresh';

function TestHarness({ onRefresh }: { onRefresh: () => Promise<void> }) {
  const ref = useRef<HTMLDivElement>(null);
  const { indicatorProps } = usePullToRefresh({ ref, onRefresh });
  return (
    <div ref={ref} data-testid="scroll-container" style={{ height: 200, overflow: 'auto' }}>
      {indicatorProps.visible && <div data-testid="pull-indicator">Refreshing</div>}
      <div style={{ height: 1000 }}>Content</div>
    </div>
  );
}

describe('usePullToRefresh', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'ontouchstart', {
      writable: true,
      configurable: true,
      value: () => {},
    });
  });

  afterEach(() => {
    delete (window as Record<string, unknown>).ontouchstart;
    vi.restoreAllMocks();
  });

  it('calls onRefresh after pulling down > 60px at scroll top', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 180 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 180 }] });
    });

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it('does NOT call onRefresh when pull distance < 60px', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');
    Object.defineProperty(container, 'scrollTop', { value: 0, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 140 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 140 }] });
    });

    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('does NOT trigger when not at scroll top', async () => {
    const onRefresh = vi.fn().mockResolvedValue(undefined);
    render(<TestHarness onRefresh={onRefresh} />);

    const container = screen.getByTestId('scroll-container');
    Object.defineProperty(container, 'scrollTop', { value: 100, writable: true });

    await act(async () => {
      fireEvent.touchStart(container, { touches: [{ clientY: 100 }] });
      fireEvent.touchMove(container, { touches: [{ clientY: 200 }] });
      fireEvent.touchEnd(container, { changedTouches: [{ clientY: 200 }] });
    });

    expect(onRefresh).not.toHaveBeenCalled();
  });
});
