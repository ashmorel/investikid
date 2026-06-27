import { describe, it, expect, vi } from 'vitest';
import { screen, act, fireEvent } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { renderMobile } from '../../../../tests/helpers/responsive';
import { BottomSheet } from '../BottomSheet';

describe('BottomSheet', () => {
  it('renders its content when open on mobile', () => {
    renderMobile(
      <BottomSheet open onOpenChange={() => {}} title="Your interest area">
        <p>Sheet body</p>
      </BottomSheet>,
    );
    expect(screen.getByRole('dialog', { name: 'Your interest area' })).toBeInTheDocument();
    expect(screen.getByText('Sheet body')).toBeInTheDocument();
  });

  it('escapes a backdrop-filter ancestor so fixed positioning anchors to the viewport', () => {
    // TopNav's <header> uses `backdrop-blur` (backdrop-filter), which makes it a
    // containing block for position:fixed descendants. A non-portaled sheet would
    // anchor `bottom-0` to that header (a thin bar at the top), rendering the panel
    // at the top of the screen. Portaling to document.body avoids this entirely.
    renderMobile(
      <div data-testid="filtered-ancestor" style={{ backdropFilter: 'blur(4px)' }}>
        <BottomSheet open onOpenChange={() => {}} title="Your interest area">
          <p>Sheet body</p>
        </BottomSheet>
      </div>,
    );

    const ancestor = screen.getByTestId('filtered-ancestor');
    const dialog = screen.getByRole('dialog', { name: 'Your interest area' });
    // The sheet must NOT live inside the filtered ancestor (it should be portaled out).
    expect(ancestor.contains(dialog)).toBe(false);
  });

  it('renders the dialog (role=dialog, aria-label) and backdrop when open', () => {
    renderMobile(
      <BottomSheet open onOpenChange={() => {}} title="Test Sheet">
        <p>Content</p>
      </BottomSheet>,
    );
    expect(screen.getByRole('dialog', { name: 'Test Sheet' })).toBeInTheDocument();
    expect(screen.getByTestId('bottom-sheet-backdrop')).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when the backdrop is clicked', () => {
    const onOpenChange = vi.fn();
    renderMobile(
      <BottomSheet open onOpenChange={onOpenChange} title="Your interest area">
        <p>Sheet body</p>
      </BottomSheet>,
    );
    screen.getByTestId('bottom-sheet-backdrop').click();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onOpenChange(false) when dragged down > 100px', () => {
    const onOpenChange = vi.fn();
    renderMobile(
      <BottomSheet open onOpenChange={onOpenChange} title="Drag Test">
        <p>Content</p>
      </BottomSheet>,
    );
    const dialog = screen.getByRole('dialog', { name: 'Drag Test' });
    fireEvent.touchStart(dialog, { touches: [{ clientY: 100 }] });
    fireEvent.touchEnd(dialog, { changedTouches: [{ clientY: 210 }] });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('does not call onOpenChange(false) when dragged down <= 100px', () => {
    const onOpenChange = vi.fn();
    renderMobile(
      <BottomSheet open onOpenChange={onOpenChange} title="Short Drag">
        <p>Content</p>
      </BottomSheet>,
    );
    const dialog = screen.getByRole('dialog', { name: 'Short Drag' });
    fireEvent.touchStart(dialog, { touches: [{ clientY: 100 }] });
    fireEvent.touchEnd(dialog, { changedTouches: [{ clientY: 190 }] });
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it('unmounts the sheet after open goes false (backstop timeout)', async () => {
    vi.useFakeTimers();
    let open = true;
    const { rerender } = renderMobile(
      <BottomSheet open={open} onOpenChange={() => {}} title="Unmount Test">
        <p>Content</p>
      </BottomSheet>,
    );
    expect(screen.getByRole('dialog', { name: 'Unmount Test' })).toBeInTheDocument();

    // Close the sheet
    open = false;
    rerender(
      <BottomSheet open={open} onOpenChange={() => {}} title="Unmount Test">
        <p>Content</p>
      </BottomSheet>,
    );

    // Before the timeout fires the sheet is still rendered (exit animation playing)
    // After advancing past 300 ms the backstop unmounts it
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    expect(screen.queryByRole('dialog', { name: 'Unmount Test' })).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it('unmounts the sheet after open goes false (animationend path)', async () => {
    let open = true;
    const { rerender } = renderMobile(
      <BottomSheet open={open} onOpenChange={() => {}} title="AnimEnd Test">
        <p>Content</p>
      </BottomSheet>,
    );
    expect(screen.getByRole('dialog', { name: 'AnimEnd Test' })).toBeInTheDocument();

    open = false;
    rerender(
      <BottomSheet open={open} onOpenChange={() => {}} title="AnimEnd Test">
        <p>Content</p>
      </BottomSheet>,
    );

    // Fire animationend on the sheet to trigger immediate unmount
    const dialog = screen.getByRole('dialog', { name: 'AnimEnd Test' });
    await act(async () => {
      fireEvent.animationEnd(dialog);
    });

    expect(screen.queryByRole('dialog', { name: 'AnimEnd Test' })).not.toBeInTheDocument();
  });

  it('renders without any framer-motion mock (no AnimatePresence required)', () => {
    // This test will fail if the component imports framer-motion and AnimatePresence
    // wraps the conditionally rendered children (the tree would need a mock).
    // Plain divs with CSS classes need no special provider.
    renderMobile(
      <BottomSheet open onOpenChange={() => {}} title="No FM Test">
        <p>No framer-motion</p>
      </BottomSheet>,
    );
    expect(screen.getByText('No framer-motion')).toBeInTheDocument();
  });

  it('has no axe a11y violations when open (vitest-axe)', async () => {
    renderMobile(
      <BottomSheet open onOpenChange={() => {}} title="A11y Test">
        <p>Accessible content</p>
      </BottomSheet>,
    );
    // Sheet is portaled to document.body; scan the full body.
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
