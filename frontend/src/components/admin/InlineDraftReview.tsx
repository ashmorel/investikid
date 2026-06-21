import { useTranslation } from 'react-i18next';
import LessonDraftReview from './LessonDraftReview';

interface InlineDraftReviewProps {
  levelId: string;
  onClose: () => void;
}

/** Collapsible inline panel wrapping the existing LessonDraftReview component.
 *  Renders review inside the Market Content tab so the operator never navigates away. */
export default function InlineDraftReview({ levelId, onClose }: InlineDraftReviewProps) {
  const { t } = useTranslation('admin');

  return (
    <div className="mt-2 rounded-md border border-line bg-card px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">{t('marketContent.review.heading')}</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-muted-foreground hover:text-ink focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {t('marketContent.review.close')}
        </button>
      </div>
      <LessonDraftReview levelId={levelId} />
    </div>
  );
}
