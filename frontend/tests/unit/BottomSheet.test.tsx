import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { BottomSheet } from '@/components/mobile/BottomSheet';

function setupMatchMedia(mobile: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => {
      const minMatch = query.match(/\(min-width:\s*(\d+)px\)/);
      const matches = minMatch ? !mobile : false;
      return {
        matches,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };
    }),
  );
}

describe('BottomSheet', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders children in a bottom sheet on mobile', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open onOpenChange={() => {}} title="Test Sheet">
        <p>Sheet content</p>
      </BottomSheet>,
    );
    expect(screen.getByText('Sheet content')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders children in fallback (dialog slot) on desktop', () => {
    setupMatchMedia(false);
    render(
      <BottomSheet
        open
        onOpenChange={() => {}}
        title="Test Sheet"
        desktopFallback={<div data-testid="desktop-fallback">Desktop</div>}
      >
        <p>Sheet content</p>
      </BottomSheet>,
    );
    expect(screen.getByTestId('desktop-fallback')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('has correct ARIA attributes on mobile', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open onOpenChange={() => {}} title="My Title">
        <p>Content</p>
      </BottomSheet>,
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('My Title')).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when backdrop is clicked', () => {
    setupMatchMedia(true);
    const onClose = vi.fn();
    render(
      <BottomSheet open onOpenChange={onClose} title="Sheet">
        <p>Content</p>
      </BottomSheet>,
    );
    const backdrop = screen.getByTestId('bottom-sheet-backdrop');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledWith(false);
  });

  it('does not render when open is false', () => {
    setupMatchMedia(true);
    render(
      <BottomSheet open={false} onOpenChange={() => {}} title="Sheet">
        <p>Hidden content</p>
      </BottomSheet>,
    );
    expect(screen.queryByText('Hidden content')).not.toBeInTheDocument();
  });
});
