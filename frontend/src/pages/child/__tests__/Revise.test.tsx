import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import Revise from '../Revise';

vi.mock('@/api/revise', () => ({ useRevisableModules: vi.fn() }));
import { useRevisableModules } from '@/api/revise';

const mockHook = useRevisableModules as unknown as ReturnType<typeof vi.fn>;

function renderPage() {
  return render(<MemoryRouter><Revise /></MemoryRouter>);
}

it('shows Daily revise + weak-first module list and is accessible', async () => {
  mockHook.mockReturnValue({
    data: [
      { module_id: 'a', title: 'Saving', icon: '🐷', topic: 'saving', due_weak_count: 2 },
      { module_id: 'b', title: 'Stocks', icon: '📈', topic: 'stocks', due_weak_count: 0 },
    ],
    isLoading: false,
  });
  const { container } = renderPage();
  expect(screen.getByRole('link', { name: /daily revise/i })).toBeInTheDocument();
  expect(screen.getByText(/2 to practice/i)).toBeInTheDocument();
  expect(await axe(container)).toHaveNoViolations();
});

it('shows an empty state when nothing is revisable', () => {
  mockHook.mockReturnValue({ data: [], isLoading: false });
  renderPage();
  expect(screen.getByText(/complete a lesson/i)).toBeInTheDocument();
});
