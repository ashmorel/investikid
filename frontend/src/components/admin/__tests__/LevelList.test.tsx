import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LevelList from '../LevelList';

const mockLevels = [
  { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, pass_threshold: 0.7, content_source: 'authored', icon: '🔰', lesson_count: 3 },
  { id: 'lv-2', module_id: 'mod-1', title: 'Advanced', order_index: 1, is_premium: true, pass_threshold: 0.8, content_source: 'authored', icon: '🏆', lesson_count: 5 },
];

const mockUpdate = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/admin', () => ({
  useLevels: () => ({ data: mockLevels, isLoading: false }),
  useUpdateLevel: () => ({ mutate: mockUpdate }),
  useDeleteLevel: () => ({ mutate: mockDelete }),
  useCreateLevel: () => ({ mutateAsync: vi.fn().mockResolvedValue({}) }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/admin/modules/mod-1/levels']}>
        <Routes>
          <Route path="/admin/modules/:moduleId/levels" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('LevelList', () => {
  it('renders both level titles', () => {
    render(<LevelList />, { wrapper });
    expect(screen.getByText('Beginner')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
  });

  it('renders Lessons, Edit, and Delete controls for each level', () => {
    render(<LevelList />, { wrapper });
    expect(screen.getAllByRole('link', { name: /lessons/i })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: /edit/i })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: /delete/i })).toHaveLength(2);
  });

  it('shows premium badge for premium levels', () => {
    render(<LevelList />, { wrapper });
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
  });

  it('renders Add Level button', () => {
    render(<LevelList />, { wrapper });
    expect(screen.getByRole('button', { name: /add level/i })).toBeInTheDocument();
  });
});
