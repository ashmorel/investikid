import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
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
});
