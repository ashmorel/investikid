import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { ReviseCard } from '../ReviseCard';

vi.mock('@/api/revise', () => ({
  useRevisableModules: vi.fn(),
}));
import { useRevisableModules } from '@/api/revise';

const mockHook = useRevisableModules as unknown as ReturnType<typeof vi.fn>;

function renderCard() {
  return render(
    <MemoryRouter>
      <ReviseCard />
    </MemoryRouter>,
  );
}

it('hides when nothing is revisable', () => {
  mockHook.mockReturnValue({ data: [] });
  const { container } = renderCard();
  expect(container).toBeEmptyDOMElement();
});

it('hides while loading (data undefined)', () => {
  mockHook.mockReturnValue({ data: undefined });
  const { container } = renderCard();
  expect(container).toBeEmptyDOMElement();
});

it('leads with the weak count when due, and is accessible', async () => {
  mockHook.mockReturnValue({
    data: [{ module_id: 'm', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 2 }],
  });
  const { container } = renderCard();
  expect(screen.getByText(/2 .*practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();
});

it('shows a keep-fresh message when nothing weak is due', () => {
  mockHook.mockReturnValue({
    data: [{ module_id: 'm', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 0 }],
  });
  renderCard();
  expect(screen.getByText(/fresh/i)).toBeInTheDocument();
});
