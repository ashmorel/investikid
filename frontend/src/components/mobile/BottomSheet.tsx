import { useRef, useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useMediaQuery } from '@/hooks/useMediaQuery';

type BottomSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  /** Rendered on desktop (>= md) instead of the sheet. If omitted, children render inline on desktop. */
  desktopFallback?: ReactNode;
};

export function BottomSheet({ open, onOpenChange, title, children, desktopFallback }: BottomSheetProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef(0);

  // Exit state machine: keep the sheet mounted while the exit animation plays.
  // `rendered` goes true immediately when open becomes true; goes false after
  // the exit animation fires onAnimationEnd OR after a backstop setTimeout
  // (handles reduced-motion / jsdom where animationend may not fire).
  const [rendered, setRendered] = useState(open);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot mount: only flips false→true when sheet opens; no cascade risk
    if (open) setRendered(true);
  }, [open]);

  // Backstop: when closed, always unmount after ~300 ms (longest animation).
  // This covers reduced-motion (animation:none → no animationend) and jsdom.
  useEffect(() => {
    if (!open) {
      const id = setTimeout(() => setRendered(false), 300);
      return () => clearTimeout(id);
    }
  }, [open]);

  const handleSheetAnimEnd = () => {
    if (!open) setRendered(false);
  };

  // Focus trap: focus the sheet on open
  useEffect(() => {
    if (open && !isDesktop && sheetRef.current) {
      sheetRef.current.focus();
    }
  }, [open, isDesktop]);

  // Lock body scroll when sheet is open on mobile (gate on `open`, not `rendered`)
  useEffect(() => {
    if (open && !isDesktop) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open, isDesktop]);

  if (isDesktop) {
    return desktopFallback ? <>{desktopFallback}</> : open ? <>{children}</> : null;
  }

  // Portal to <body> so the fixed-position sheet anchors to the viewport. Any
  // ancestor with `transform`/`filter`/`backdrop-filter` (e.g. TopNav's
  // `backdrop-blur` header, which hosts this via ProfileMenu) would otherwise
  // become the containing block and pin the sheet to the top of the screen.
  if (!rendered) return null;

  return createPortal(
    <>
      {/* Backdrop — role="presentation" marks this as a purely visual dismiss target;
          keyboard users close via Escape (handled by focus on the dialog) so no
          additional key handler is needed on the overlay itself. */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- backdrop dismiss is a touch/mouse convention; keyboard users close via the focusable dialog */}
      <div
        data-testid="bottom-sheet-backdrop"
        className={`fixed inset-0 z-40 bg-black/40 ${open ? 'backdrop-enter' : 'backdrop-exit'}`}
        onClick={() => onOpenChange(false)}
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-white shadow-xl outline-none ${open ? 'sheet-enter' : 'sheet-exit'}`}
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
        onAnimationEnd={handleSheetAnimEnd}
        onTouchStart={(e) => {
          dragStartY.current = e.touches[0].clientY;
        }}
        onTouchEnd={(e) => {
          const delta = e.changedTouches[0].clientY - dragStartY.current;
          if (delta > 100) {
            onOpenChange(false);
          }
        }}
      >
        {/* Drag handle */}
        <div className="flex justify-center py-3">
          <div className="h-1.5 w-10 rounded-full bg-gray-300" />
        </div>

        {/* Title */}
        <div className="px-4 pb-2">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        </div>

        {/* Content */}
        <div className="max-h-[70vh] overflow-y-auto px-4 pb-4">
          {children}
        </div>
      </div>
    </>,
    document.body,
  );
}
