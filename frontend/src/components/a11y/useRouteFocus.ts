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
    // Start each new route at the top so the header (logo + nav tabs) is
    // visible — matching what users expect when switching tabs.
    window.scrollTo({ top: 0, left: 0 });
    const main = document.getElementById('main');
    if (main) {
      // preventScroll: keep the a11y focus move WITHOUT the browser scrolling
      // a taller-than-viewport <main> to the top of the screen, which hid the
      // header on long pages (Stats/Progress/Simulator) while short pages
      // (Home/Learn) were unaffected.
      main.focus({ preventScroll: true });
    }
    const title = document.title || 'Page updated';
    announce(title);
  }, [pathname, announce]);
}
