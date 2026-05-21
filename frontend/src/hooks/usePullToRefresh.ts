import { useState, useEffect, useCallback, useRef, type RefObject } from 'react';

const PULL_THRESHOLD = 60;

type UsePullToRefreshOptions = {
  ref: RefObject<HTMLElement | null>;
  onRefresh: () => Promise<void>;
};

type IndicatorProps = {
  visible: boolean;
  progress: number; // 0..1 while pulling, stays 1 while refreshing
};

export function usePullToRefresh({ ref, onRefresh }: UsePullToRefreshOptions) {
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef(0);
  const pulling = useRef(false);
  const pullDistanceRef = useRef(0);

  const isTouchDevice = typeof window !== 'undefined' && 'ontouchstart' in window;

  const handleTouchStart = useCallback(
    (e: TouchEvent) => {
      const el = ref.current;
      if (!el || el.scrollTop > 0 || refreshing) return;
      startY.current = e.touches[0].clientY;
      pulling.current = true;
      setPullDistance(0);
      pullDistanceRef.current = 0;
    },
    [ref, refreshing],
  );

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!pulling.current) return;
    const delta = e.touches[0].clientY - startY.current;
    if (delta > 0) {
      setPullDistance(delta);
      pullDistanceRef.current = delta;
    }
  }, []);

  const handleTouchEnd = useCallback(async () => {
    if (!pulling.current) return;
    pulling.current = false;
    const distance = pullDistanceRef.current;
    if (distance >= PULL_THRESHOLD) {
      setRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
      }
    }
    setPullDistance(0);
    pullDistanceRef.current = 0;
  }, [onRefresh]);

  useEffect(() => {
    const el = ref.current;
    if (!el || !isTouchDevice) return;

    el.addEventListener('touchstart', handleTouchStart, { passive: true });
    el.addEventListener('touchmove', handleTouchMove, { passive: true });
    el.addEventListener('touchend', handleTouchEnd);

    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchmove', handleTouchMove);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, [ref, isTouchDevice, handleTouchStart, handleTouchMove, handleTouchEnd]);

  const indicatorProps: IndicatorProps = {
    visible: refreshing || pullDistance > 10,
    progress: refreshing ? 1 : Math.min(pullDistance / PULL_THRESHOLD, 1),
  };

  return { indicatorProps, refreshing };
}
