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

let CoachPennyPanel: typeof import('@/components/child/lesson/CoachPennyPanel').CoachPennyPanel;

beforeEach(async () => {
  CoachPennyPanel = (await import('@/components/child/lesson/CoachPennyPanel')).CoachPennyPanel;
});

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CoachPennyPanel lessonId="lesson-1" onClose={() => {}} />
    </QueryClientProvider>,
  );
}

describe('CoachPennyPanel', () => {
  it('shows a friendly error when the tutor request fails', async () => {
    renderPanel();
    await userEvent.type(screen.getByPlaceholderText('Ask Coach Penny...'), 'What is a stock?');
    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/couldn't answer/i),
    );
  });
});
