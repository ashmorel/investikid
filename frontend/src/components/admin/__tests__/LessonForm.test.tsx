import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LessonForm from '../LessonForm';

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock('@/api/admin', () => ({
  useCreateLesson: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: mockUpdate, isPending: false }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('LessonForm', () => {
  it('renders type selector with card, quiz, scenario', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByRole('button', { name: /card/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /quiz/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /scenario/i })).toBeInTheDocument();
  });

  it('shows card fields by default', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/body/i)).toBeInTheDocument();
  });

  it('shows quiz fields when quiz type selected', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /quiz/i }));
    expect(screen.getByLabelText(/question/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/explanation/i)).toBeInTheDocument();
  });

  it('shows scenario fields when scenario type selected', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /scenario/i }));
    expect(screen.getByLabelText(/prompt/i)).toBeInTheDocument();
  });

  it('renders XP reward field', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByLabelText(/xp reward/i)).toBeInTheDocument();
  });
});
