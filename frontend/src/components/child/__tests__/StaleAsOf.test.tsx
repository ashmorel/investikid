import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { I18nextProvider } from 'react-i18next';
import { i18n } from '@/i18n';
import { StaleAsOf, formatAsOf } from '../StaleAsOf';

vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn() }));
import { useOnline } from '@/hooks/useOnline';
const mockOnline = vi.mocked(useOnline);

function renderLabel(updatedAt: number) {
  return render(<I18nextProvider i18n={i18n}><StaleAsOf updatedAt={updatedAt} /></I18nextProvider>);
}

describe('formatAsOf', () => {
  it('shows time only for today, date+time otherwise', () => {
    const now = new Date('2026-06-27T15:00:00');
    expect(formatAsOf(new Date('2026-06-27T14:34:00').getTime(), now)).toMatch(/2:34/);
    expect(formatAsOf(new Date('2026-06-26T14:34:00').getTime(), now)).toMatch(/Jun 26/);
  });
});

describe('StaleAsOf', () => {
  it('shows "Prices as of <time>" when offline with data', () => {
    mockOnline.mockReturnValue(false);
    renderLabel(new Date('2026-06-27T14:34:00').getTime());
    expect(screen.getByText(/Prices as of/i)).toBeInTheDocument();
  });
  it('renders nothing when online', () => {
    mockOnline.mockReturnValue(true);
    const { container } = renderLabel(Date.now());
    expect(container).toBeEmptyDOMElement();
  });
  it('renders nothing when there is no cached data', () => {
    mockOnline.mockReturnValue(false);
    const { container } = renderLabel(0);
    expect(container).toBeEmptyDOMElement();
  });
});
