import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/api/ai', async () => {
  const actual = await vi.importActual('@/api/ai');
  return {
    ...actual,
    aiApi: {
      ...((actual as { aiApi?: object }).aiApi ?? {}),
      sendTutorMessage: vi.fn().mockRejectedValue(new Error('503')),
    },
  };
});

let CoachEddiePanel: typeof import('@/components/child/lesson/CoachEddiePanel').CoachEddiePanel;

beforeEach(async () => {
  CoachEddiePanel = (await import('@/components/child/lesson/CoachEddiePanel')).CoachEddiePanel;
});

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CoachEddiePanel lessonId="lesson-1" onClose={() => {}} />
    </QueryClientProvider>,
  );
}

describe('CoachEddiePanel', () => {
  it('shows a friendly error when the tutor request fails', async () => {
    renderPanel();
    await userEvent.type(screen.getByPlaceholderText('Ask Coach Eddie...'), 'What is a stock?');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/couldn't answer/i),
    );
  });
});
