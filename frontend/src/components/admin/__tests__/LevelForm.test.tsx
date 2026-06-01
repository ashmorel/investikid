import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LevelForm from '../LevelForm';

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock('@/api/admin', () => ({
  useCreateLevel: () => ({ mutateAsync: mockCreate }),
  useUpdateLevel: () => ({ mutateAsync: mockUpdate }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('LevelForm', () => {
  it('renders all five fields', () => {
    render(<LevelForm moduleId="mod-1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/order index/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pass threshold/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/icon/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/premium/i)).toBeInTheDocument();
  });

  it('calls create hook with expected payload on submit', async () => {
    const onClose = vi.fn();
    render(<LevelForm moduleId="mod-1" nextOrderIndex={2} onClose={onClose} />, { wrapper });

    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Beginner' } });
    fireEvent.change(screen.getByLabelText(/icon/i), { target: { value: '🔰' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Beginner', order_index: 2, is_premium: false, icon: '🔰' })
      );
    });
    expect(onClose).toHaveBeenCalled();
  });
});
