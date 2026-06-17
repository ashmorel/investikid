import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { LanguageSwitcher } from '../LanguageSwitcher';

vi.mock('../../../hooks/useLanguage', () => ({
  useLanguage: () => ({ current: 'en', setLanguage: vi.fn() }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe('LanguageSwitcher', () => {
  it('renders a labelled control listing only available languages', () => {
    render(wrap(<LanguageSwitcher />));
    expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'English' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Español' })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<LanguageSwitcher />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
