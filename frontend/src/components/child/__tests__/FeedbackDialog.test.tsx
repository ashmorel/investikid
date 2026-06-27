import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FeedbackDialog } from '../FeedbackDialog';
import * as client from '@/api/client';

// Screenshot capture/compression touches canvas + the modern-screenshot lib,
// neither of which runs in jsdom — mock the seam.
vi.mock('@/lib/screenshot', () => ({
  captureScreen: vi.fn(async () => 'data:image/jpeg;base64,CAPTURED'),
  fileToScreenshot: vi.fn(async () => 'data:image/jpeg;base64,UPLOADED'),
}));

function renderDialog(audience: 'child' | 'parent' = 'child') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <FeedbackDialog open onOpenChange={() => {}} audience={audience} />
    </QueryClientProvider>,
  );
}

describe('FeedbackDialog', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('shows the type and message fields', () => {
    renderDialog();
    expect(screen.getByLabelText('Type')).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toBeInTheDocument();
  });

  it('updates the character counter', () => {
    renderDialog();
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'hello' } });
    expect(screen.getByText('5 / 2000')).toBeInTheDocument();
  });

  it('submits feedback and posts to /feedback', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 'abc' });
    renderDialog();
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'a bug' } });
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(spy.mock.calls[0][0]).toBe('/feedback');
  });

  it('offers screenshot capture and upload controls', () => {
    renderDialog();
    expect(screen.getByRole('button', { name: /capture screen/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^upload$/i })).toBeInTheDocument();
  });

  it('attaches an uploaded screenshot and includes it in the submit', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 'abc' });
    renderDialog();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['x'], 'shot.png', { type: 'image/png' });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Preview appears once the (mocked) compression resolves.
    await screen.findByRole('img', { name: /attached screenshot/i });

    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'a bug' } });
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }));

    await waitFor(() => expect(spy).toHaveBeenCalled());
    const bodyStr = (spy.mock.calls[0][1] as { body: string }).body;
    expect(bodyStr).toContain('data:image/jpeg;base64,UPLOADED');
  });
});
