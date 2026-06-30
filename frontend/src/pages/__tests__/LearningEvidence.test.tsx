import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LearningEvidence from '../LearningEvidence';

// No auth, no API calls needed — this is a static public page.
vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no network in /how-we-measure'))));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/how-we-measure']}>
      <Routes>
        <Route path="/how-we-measure" element={<LearningEvidence />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LearningEvidence page (public, no auth)', () => {
  it('renders a top-level heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('renders a how-we-measure-mastery section heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /how we measure mastery/i })).toBeInTheDocument();
  });

  it('renders a standards-alignment section heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /standards alignment/i })).toBeInTheDocument();
  });

  it('renders a safety section heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /safety/i })).toBeInTheDocument();
  });

  it('renders a privacy section heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /privacy/i })).toBeInTheDocument();
  });

  it('does not include any efficacy percentage claims', () => {
    const { container } = renderPage();
    expect(container.textContent).not.toMatch(/\+\d+%/);
    expect(container.textContent).not.toMatch(/\d+% (better|improvement|gain|increase)/i);
  });

  it('has no axe accessibility violations', async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });
});
