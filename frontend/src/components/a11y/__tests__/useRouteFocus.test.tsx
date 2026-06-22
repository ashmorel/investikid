import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useRouteFocus } from '../useRouteFocus';

function Harness({ go }: { go?: string }) {
  useRouteFocus();
  const navigate = useNavigate();
  useEffect(() => {
    if (go) navigate(go);
  }, [go, navigate]);
  return <main id="main" tabIndex={-1}>content</main>;
}

function renderAt(go?: string) {
  return render(
    <MemoryRouter initialEntries={['/home']}>
      <Routes>
        <Route path="*" element={<Harness go={go} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('useRouteFocus', () => {
  beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not scroll on the first render', () => {
    renderAt();
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it('scrolls to the top and focuses main without scrolling on route change', () => {
    const focusSpy = vi.spyOn(HTMLElement.prototype, 'focus');
    renderAt('/stats');
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, left: 0 });
    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });
  });
});
