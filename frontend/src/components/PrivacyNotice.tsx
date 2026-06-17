import { useTranslation } from 'react-i18next';
import { PRIVACY_NOTICE_VERSION } from '@/api/auth';

/**
 * The privacy notice body — shared between the standalone /privacy page
 * and the modal shown during signup (so the content lives in one place).
 */
export function PrivacyNotice() {
  const { t } = useTranslation('parent');
  return (
    <div>
      <p className="text-sm text-muted-foreground">
        {t('privacyNotice.meta', { version: PRIVACY_NOTICE_VERSION })}
      </p>

      <p className="mt-4 text-sm">
        {t('privacyNotice.intro')}
      </p>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.whatIsApp.heading')}</h2>
        <p className="mt-2 text-sm">
          {t('privacyNotice.whatIsApp.body')}
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.whatWeCollect.heading')}</h2>
        <p className="mt-2 text-sm">{t('privacyNotice.whatWeCollect.intro')}</p>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>{t('privacyNotice.whatWeCollect.usernameLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.usernameDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.dobLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.dobDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.countryLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.countryDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.passwordLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.passwordDesc')}`}</li>
        </ul>
        <p className="mt-3 text-sm">{t('privacyNotice.whatWeCollect.alsoCollect')}</p>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>{t('privacyNotice.whatWeCollect.emailLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.emailDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.parentEmailLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.parentEmailDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.progressLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.progressDesc')}`}</li>
          <li><strong>{t('privacyNotice.whatWeCollect.topicsLabel')}</strong>{` — ${t('privacyNotice.whatWeCollect.topicsDesc')}`}</li>
        </ul>
        <p className="mt-3 text-sm">{t('privacyNotice.whatWeCollect.notCollectedPre')} <strong>{t('privacyNotice.whatWeCollect.notCollectedNot')}</strong>{` ${t('privacyNotice.whatWeCollect.notCollectedPost')}`}</p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.whyWeCollect.heading')}</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>{t('privacyNotice.whyWeCollect.loginSafelyLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.loginSafelyDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.checkAgeLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.checkAgeDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.countryRulesLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.countryRulesDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.parentPermissionLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.parentPermissionDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.rememberProgressLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.rememberProgressDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.topicChoiceLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.topicChoiceDesc')}`}</li>
          <li><strong>{t('privacyNotice.whyWeCollect.emailMessagesLabel')}</strong>{` — ${t('privacyNotice.whyWeCollect.emailMessagesDesc')}`}</li>
        </ul>
        <p className="mt-3 text-sm">
          {t('privacyNotice.whyWeCollect.onlyToRun')}
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.whoCanSee.heading')}</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>{t('privacyNotice.whoCanSee.youLabel')}</strong>{` — ${t('privacyNotice.whoCanSee.youDesc')}`}</li>
          <li><strong>{t('privacyNotice.whoCanSee.parentLabel')}</strong>{` — ${t('privacyNotice.whoCanSee.parentDesc')}`}</li>
          <li><strong>{t('privacyNotice.whoCanSee.teamLabel')}</strong>{` — ${t('privacyNotice.whoCanSee.teamDesc')}`}</li>
        </ul>
        <p className="mt-3 text-sm">
          {t('privacyNotice.whoCanSee.noSharePre')} <strong>{t('privacyNotice.whoCanSee.noShareNot')}</strong>{` ${t('privacyNotice.whoCanSee.noSharePost')}`}
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.youtube.heading')}</h2>
        <p className="mt-2 text-sm">
          {t('privacyNotice.youtube.body')}
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.retention.heading')}</h2>
        <p className="mt-2 text-sm">
          {t('privacyNotice.retention.body')}
        </p>
        <p className="mt-2 text-sm">{t('privacyNotice.retention.deletionIntro')}</p>
        <ol className="mt-2 list-decimal pl-5 text-sm space-y-1">
          <li>{t('privacyNotice.retention.step1')}</li>
          <li>{t('privacyNotice.retention.step2')}</li>
          <li>{t('privacyNotice.retention.step3')}</li>
        </ol>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.yourChoices.heading')}</h2>
        <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
          <li><strong>{t('privacyNotice.yourChoices.recommendationsLabel')}</strong>{` — ${t('privacyNotice.yourChoices.recommendationsDesc')}`}</li>
          <li><strong>{t('privacyNotice.yourChoices.marketingLabel')}</strong>{` — ${t('privacyNotice.yourChoices.marketingDesc')}`}</li>
          <li><strong>{t('privacyNotice.yourChoices.deleteAccountLabel')}</strong>{` — ${t('privacyNotice.yourChoices.deleteAccountDesc')}`}</li>
          <li><strong>{t('privacyNotice.yourChoices.seeDataLabel')}</strong>{` — ${t('privacyNotice.yourChoices.seeDataDesc')}`}</li>
          <li><strong>{t('privacyNotice.yourChoices.fixInfoLabel')}</strong>{` — ${t('privacyNotice.yourChoices.fixInfoDesc')}`}</li>
        </ul>
        <p className="mt-3 text-sm text-muted-foreground">
          {t('privacyNotice.yourChoices.minorNote')}
        </p>
      </section>

      <section className="mt-6">
        <h2 className="text-lg font-semibold">{t('privacyNotice.contact.heading')}</h2>
        <p className="mt-2 text-sm">
          {t('privacyNotice.contact.bodyPre')}{' '}
          <strong>{t('privacyNotice.contact.email')}</strong>.{' '}
          {t('privacyNotice.contact.bodyPost')}
        </p>
        <p className="mt-2 text-sm">
          {t('privacyNotice.contact.complain')}
        </p>
      </section>
    </div>
  );
}
