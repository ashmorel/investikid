import { useEffect, useRef, type RefObject } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMediaQuery } from './useMediaQuery';

const TABS = ['/home', '/lessons', '/simulator', '/stats'] as const;
const SWIPE_THRESHOLD = 50; // px
const VELOCITY_THRESHOLD = 0.3; // px/ms

type UseSwipeNavOptions = {
  ref: RefObject<HTMLElement | null>;
};

export function useSwipeNav({ ref }: UseSwipeNavOptions) {
  const navigate = useNavigate();
  const location = useLocation();
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const startX = useRef(0);
  const startY = useRef(0);
  const startTime = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || isDesktop) return;

    const handleTouchStart = (e: TouchEvent) => {
      startX.current = e.touches[0].clientX;
      startY.current = e.touches[0].clientY;
      startTime.current = e.timeStamp;
    };

    const handleTouchEnd = (e: TouchEvent) => {
      const dx = e.changedTouches[0].clientX - startX.current;
      const dy = e.changedTouches[0].clientY - startY.current;
      const dt = e.timeStamp - startTime.current;

      // Ignore vertical swipes
      if (Math.abs(dy) > Math.abs(dx)) return;
      // Ignore short swipes
      if (Math.abs(dx) < SWIPE_THRESHOLD) return;
      // Ignore slow swipes
      if (dt > 0 && Math.abs(dx) / dt < VELOCITY_THRESHOLD) return;

      // Check if we're swiping from a scrollable element
      const target = e.target as HTMLElement;
      if (target.closest('[data-swipe-ignore]') || target.closest('.overflow-x-auto')) return;

      const currentPath = location.pathname;
      const currentIdx = TABS.indexOf(currentPath as (typeof TABS)[number]);
      if (currentIdx === -1) return;

      if (dx < 0 && currentIdx < TABS.length - 1) {
        // Swipe left → next tab
        navigate(TABS[currentIdx + 1]);
      } else if (dx > 0 && currentIdx > 0) {
        // Swipe right → prev tab
        navigate(TABS[currentIdx - 1]);
      }
    };

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, [ref, isDesktop, navigate, location.pathname]);
}
