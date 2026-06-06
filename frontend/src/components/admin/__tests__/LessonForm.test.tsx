import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LessonForm from '../LessonForm';

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});
const mockCreateLevelLesson = vi.fn().mockResolvedValue({});

vi.mock('@/api/admin', () => ({
  useCreateLesson: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: mockUpdate, isPending: false }),
  useCreateLevelLesson: () => ({ mutateAsync: mockCreateLevelLesson, isPending: false }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('LessonForm', () => {
  beforeEach(() => {
    mockCreate.mockClear();
    mockUpdate.mockClear();
    mockCreateLevelLesson.mockClear();
  });

  it('renders type selector with card, quiz, scenario', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByRole('button', { name: /card/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /quiz/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /scenario/i })).toBeInTheDocument();
  });

  it('renders type selector with video', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByRole('button', { name: /video/i })).toBeInTheDocument();
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

  it('shows video fields when video type selected', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /video/i }));
    expect(screen.getByLabelText(/youtube url or id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/caption/i)).toBeInTheDocument();
  });

  it('extracts youtube_id from full URL on submit', async () => {
    const onClose = vi.fn();
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={onClose} />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /video/i }));

    const youtubeInput = screen.getByLabelText(/youtube url or id/i);
    fireEvent.change(youtubeInput, { target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' } });

    const form = youtubeInput.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'video',
          content_json: expect.objectContaining({ youtube_id: 'dQw4w9WgXcQ' }),
        })
      );
    });
  });

  it('shows apply-mission fields when the mission toggle is enabled', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByLabelText(/apply mission/i));
    expect(screen.getByLabelText(/mission type/i)).toBeInTheDocument();
  });

  it('includes apply_mission in the create payload when enabled', async () => {
    const onClose = vi.fn();
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={onClose} />, { wrapper });

    fireEvent.change(screen.getByLabelText(/^title/i), { target: { value: 'T' } });
    fireEvent.change(screen.getByLabelText(/body/i), { target: { value: 'B' } });
    fireEvent.click(screen.getByLabelText(/apply mission/i));

    const form = screen.getByLabelText(/mission type/i).closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          apply_mission: expect.objectContaining({ mission_type: 'first_buy' }),
        })
      );
    });
  });

  it('calls level endpoint when levelId is provided', async () => {
    const onClose = vi.fn();
    render(<LessonForm moduleId="m1" levelId="lv1" nextOrderIndex={0} onClose={onClose} />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /video/i }));

    const youtubeInput = screen.getByLabelText(/youtube url or id/i);
    fireEvent.change(youtubeInput, { target: { value: 'dQw4w9WgXcQ' } });

    const form = youtubeInput.closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockCreateLevelLesson).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'video',
          content_json: expect.objectContaining({ youtube_id: 'dQw4w9WgXcQ' }),
        })
      );
      expect(mockCreate).not.toHaveBeenCalled();
    });
  });
});
