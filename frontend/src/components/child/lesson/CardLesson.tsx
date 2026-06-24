import { useTranslation } from 'react-i18next';
import { GradientButton } from '@/components/child/ui/GradientButton';

type Props = { contentJson: { title?: string; body?: string }; onComplete: (score: number | null) => void; illustration?: React.ReactNode; onShowPenny?: () => void; completing?: boolean };

export function CardLesson({ contentJson, onComplete, illustration, onShowPenny, completing = false }: Props) {
  const { t } = useTranslation('lessons');
  return (
    <div className="space-y-5 rounded-3xl bg-white p-6 text-center shadow-lg shadow-brand-600/10">
      {illustration && <div className="flex justify-center">{illustration}</div>}
      <h2 className="text-2xl font-extrabold leading-tight text-gray-900">{contentJson.title ?? ''}</h2>
      <p className="text-[15px] leading-relaxed text-gray-600">{contentJson.body ?? ''}</p>
      <GradientButton full onClick={() => onComplete(null)} disabled={completing}>{completing ? t('card.saving') : t('card.gotIt')}</GradientButton>
      {onShowPenny && (
        <button type="button" onClick={onShowPenny} className="text-sm font-bold text-brand-700 underline hover:text-brand-800">
          {t('card.askCoachPenny')}
        </button>
      )}
    </div>
  );
}
