import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { describe, expect, it } from 'vitest';
import { useTranslation } from 'react-i18next';
import { i18n, initI18n } from '../../src/i18n';

function Probe() {
  const { t } = useTranslation();
  return <span>{t('appName')}</span>;
}

describe('i18n init', () => {
  it('renders a key from the en catalog', async () => {
    await initI18n('en');
    render(
      <I18nextProvider i18n={i18n}>
        <Probe />
      </I18nextProvider>,
    );
    expect(screen.getByText('InvestiKid')).toBeInTheDocument();
  });
});
