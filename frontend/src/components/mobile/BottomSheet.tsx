import { useRef, useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
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
  const prefersReducedMotion = useReducedMotion();
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef(0);

  // Focus trap: focus the sheet on open
  useEffect(() => {
    if (open && !isDesktop && sheetRef.current) {
      sheetRef.current.focus();
    }
  }, [open, isDesktop]);

  // Lock body scroll when sheet is open on mobile
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
  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            data-testid="bottom-sheet-backdrop"
            className="fixed inset-0 z-40 bg-black/40"
            initial={prefersReducedMotion ? false : { opacity: 0 }}
            animate={prefersReducedMotion ? undefined : { opacity: 1 }}
            exit={prefersReducedMotion ? undefined : { opacity: 0 }}
            onClick={() => onOpenChange(false)}
          />

          {/* Sheet */}
          <motion.div
            ref={sheetRef}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-white shadow-xl outline-none"
            style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            initial={prefersReducedMotion ? false : { y: '100%' }}
            animate={prefersReducedMotion ? undefined : { y: 0 }}
            exit={prefersReducedMotion ? undefined : { y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
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
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  );
}
