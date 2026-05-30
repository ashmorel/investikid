import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FeedbackDialog } from '../FeedbackDialog';
import * as client from '@/api/client';

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
});
