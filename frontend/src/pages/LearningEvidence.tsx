import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

// ⚙️ operator/legal-reviewable before launch:
// All copy in this file is drawn from i18n keys in parent.json under the
// "evidence" namespace section. Review the following before going live:
//   - evidence.standards.body   — verify MaPS / CCSS framework tag wording
//   - evidence.privacy.*        — align with the current privacy notice version
//   - evidence.safety.*         — confirm moderation pipeline description is current
// No efficacy/outcome percentages are claimed anywhere in this page (OD4 constraint).

/**
 * Public static page — no auth, no API calls, no user data.
 * Explains how InvestiKid measures learning, its curriculum standards,
 * content safety posture, and children's-privacy commitments.
 * Route: /how-we-measure
 */
export default function LearningEvidence() {
  const { t } = useTranslation('parent');

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      {/* Page header */}
      <header className="mb-10 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          {t('evidence.pageTitle')}
        </h1>
        <p className="mt-3 text-base text-gray-600">{t('evidence.pageSubtitle')}</p>
      </header>

      {/* Section 1: How we measure mastery */}
      <section aria-labelledby="evidence-mastery-heading" className="mb-10">
        <h2
          id="evidence-mastery-heading"
          className="mb-4 text-xl font-bold text-gray-900"
        >
          {t('evidence.howWeMeasure.heading')}
        </h2>

        <div className="space-y-6 rounded-2xl border border-brand-100 bg-brand-50 p-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.howWeMeasure.diagnosticHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.howWeMeasure.diagnosticBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.howWeMeasure.progressChecksHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.howWeMeasure.progressChecksBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.howWeMeasure.taxonomyHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.howWeMeasure.taxonomyBody')}
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Standards alignment */}
      <section aria-labelledby="evidence-standards-heading" className="mb-10">
        <h2
          id="evidence-standards-heading"
          className="mb-4 text-xl font-bold text-gray-900"
        >
          {t('evidence.standards.heading')}
        </h2>

        <div className="rounded-2xl border border-brand-100 bg-brand-50 p-6">
          <p className="text-sm text-gray-700">{t('evidence.standards.body')}</p>
          <p className="mt-3 text-xs text-gray-500 italic">{t('evidence.standards.note')}</p>
        </div>
      </section>

      {/* Section 3: Safety */}
      <section aria-labelledby="evidence-safety-heading" className="mb-10">
        <h2
          id="evidence-safety-heading"
          className="mb-4 text-xl font-bold text-gray-900"
        >
          {t('evidence.safety.heading')}
        </h2>

        <div className="space-y-6 rounded-2xl border border-brand-100 bg-brand-50 p-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.safety.aiModerationHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.safety.aiModerationBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.safety.curatedHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.safety.curatedBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.safety.designedForKidsHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.safety.designedForKidsBody')}
            </p>
          </div>
        </div>
      </section>

      {/* Section 4: Privacy */}
      <section aria-labelledby="evidence-privacy-heading" className="mb-10">
        <h2
          id="evidence-privacy-heading"
          className="mb-4 text-xl font-bold text-gray-900"
        >
          {t('evidence.privacy.heading')}
        </h2>

        <div className="space-y-6 rounded-2xl border border-brand-100 bg-brand-50 p-6">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.privacy.consentHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.privacy.consentBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.privacy.minimisationHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.privacy.minimisationBody')}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {t('evidence.privacy.noExposureHeading')}
            </h3>
            <p className="mt-1 text-sm text-gray-700">
              {t('evidence.privacy.noExposureBody')}
            </p>
          </div>

          <p className="pt-2">
            <Link
              to={t('evidence.privacy.learnMoreHref')}
              className="text-sm font-medium text-brand-700 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
            >
              {t('evidence.privacy.learnMore')}
            </Link>
          </p>
        </div>
      </section>

      {/* Footer CTA */}
      <div className="text-center">
        <Link
          to="/try"
          className="inline-block min-h-[44px] rounded-full bg-brand-gradient px-6 py-3 text-sm font-extrabold text-white shadow hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
        >
          {t('evidence.backToTry')}
        </Link>
      </div>
    </main>
  );
}
