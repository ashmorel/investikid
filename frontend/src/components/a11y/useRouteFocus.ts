import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAnnounce } from './useAnnounce';

export function useRouteFocus() {
  const { pathname } = useLocation();
  const announce = useAnnounce();
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const main = document.getElementById('main');
    if (main) {
      main.focus({ preventScroll: false });
    }
    const title = document.title || 'Page updated';
    announce(title);
  }, [pathname, announce]);
}
