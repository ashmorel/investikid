// Use the real react-i18next library (not the global catalog mock) so that
// initI18n wiring is exercised against the genuine i18next stack.
vi.unmock('react-i18next');

import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { describe, expect, it, vi } from 'vitest';
import { useTranslation } from 'react-i18next';
import { i18n, initI18n } from '../../src/i18n';

function Probe() {
  const { t } = useTranslation();
  return <span>{t('appName')}</span>;
}

describe('i18n init', () => {
  it('renders a key from the en catalog', async () => {
    await initI18n('en');
    // Ensure the active language is 'en' regardless of prior test runs that may
    // have changed it (initI18n is idempotent when already initialized).
    await i18n.changeLanguage('en');
    render(
      <I18nextProvider i18n={i18n}>
        <Probe />
      </I18nextProvider>,
    );
    expect(screen.getByText('InvestiKid')).toBeInTheDocument();
  });
});
