import { it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useRouteFocus } from '@/components/a11y/useRouteFocus';
import { LiveRegion } from '@/components/a11y/LiveRegion';

function Layout() {
  useRouteFocus();
  return (
    <>
      <main id="main" tabIndex={-1}>main</main>
      <Nav />
    </>
  );
}

function Nav() {
  const navigate = useNavigate();
  return <button onClick={() => navigate('/b')}>go b</button>;
}

it('moves focus to #main and announces on route change', async () => {
  document.title = 'Page B — Invest-Ed';
  render(
    <LiveRegion>
      <MemoryRouter initialEntries={['/a']}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/a" element={<div>a</div>} />
            <Route path="/b" element={<div>b</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </LiveRegion>,
  );
  await act(async () => { screen.getByText('go b').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 1)); });
  expect(document.activeElement?.id).toBe('main');
  expect(screen.getByRole('status')).toHaveTextContent(/Page B/);
});
