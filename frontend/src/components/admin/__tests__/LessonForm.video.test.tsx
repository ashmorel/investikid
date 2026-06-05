import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LessonForm from '../LessonForm';

const mockCreate = vi.fn().mockResolvedValue({});
const mockUpdate = vi.fn().mockResolvedValue({});
const mockCreateLevelLesson = vi.fn().mockResolvedValue({});
const presignVideo = vi.fn();
const uploadToPresigned = vi.fn();

vi.mock('@/api/admin', () => ({
  useCreateLesson: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateLesson: () => ({ mutateAsync: mockUpdate, isPending: false }),
  useCreateLevelLesson: () => ({ mutateAsync: mockCreateLevelLesson, isPending: false }),
  presignVideo: (...args: unknown[]) => presignVideo(...args),
  uploadToPresigned: (...args: unknown[]) => uploadToPresigned(...args),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe('LessonForm hosted video', () => {
  beforeEach(() => {
    mockCreate.mockClear();
    mockUpdate.mockClear();
    mockCreateLevelLesson.mockClear();
    presignVideo.mockReset().mockResolvedValue({
      asset_id: 'a1',
      key: 'videos/x.mp4',
      upload_url: 'https://r2/PUT',
      public_url: 'https://cdn/videos/x.mp4',
    });
    uploadToPresigned.mockReset().mockResolvedValue(undefined);
  });

  it('shows a file input when source is switched to Uploaded', () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /video/i }));
    // YouTube field is shown by default
    expect(screen.getByLabelText(/youtube url or id/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: /upload/i }));
    expect(screen.getByLabelText(/video file/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/youtube url or id/i)).not.toBeInTheDocument();
  });

  it('uploads a file and saves a hosted content_json with the returned video_url', async () => {
    const onClose = vi.fn();
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={onClose} />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /video/i }));
    fireEvent.click(screen.getByRole('radio', { name: /upload/i }));

    const file = new File([new Uint8Array([1, 2, 3])], 'lesson.mp4', { type: 'video/mp4' });
    await userEvent.upload(screen.getByLabelText(/video file/i), file);

    await waitFor(() => expect(presignVideo).toHaveBeenCalledWith('lesson.mp4', 'video/mp4', file.size));
    await waitFor(() => expect(uploadToPresigned).toHaveBeenCalled());
    // preview appears with the returned public_url
    await waitFor(() => {
      const video = document.querySelector('video');
      expect(video).not.toBeNull();
      expect(video).toHaveAttribute('src', 'https://cdn/videos/x.mp4');
    });

    const form = screen.getByLabelText(/video file/i).closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'video',
          content_json: expect.objectContaining({
            video_source: 'hosted',
            video_url: 'https://cdn/videos/x.mp4',
          }),
        }),
      );
    });
  });

  it('rejects a non-mp4 file without calling presign', async () => {
    render(<LessonForm moduleId="m1" nextOrderIndex={0} onClose={vi.fn()} />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: /video/i }));
    fireEvent.click(screen.getByRole('radio', { name: /upload/i }));

    const file = new File([new Uint8Array([1])], 'lesson.mov', { type: 'video/quicktime' });
    await userEvent.upload(screen.getByLabelText(/video file/i), file);

    expect(presignVideo).not.toHaveBeenCalled();
    expect(await screen.findByText(/mp4/i)).toBeInTheDocument();
  });
});
