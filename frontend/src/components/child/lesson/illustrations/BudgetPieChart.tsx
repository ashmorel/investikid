import { useTranslation } from 'react-i18next';

export function BudgetPieChart() {
  const { t } = useTranslation('child');
  return (
    <div className="flex items-center justify-center gap-6 rounded-xl bg-gradient-to-br from-brand-100 to-brand-200 p-6">
      <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
        <circle cx="70" cy="70" r="60" fill="#dbeafe" />
        <path d="M70,70 L70,10 A60,60 0 0,1 122,100 Z" fill="#3b82f6" />
        <path d="M70,70 L122,100 A60,60 0 0,1 18,100 Z" fill="#f59e0b" aria-hidden="true" />
        <path d="M70,70 L18,100 A60,60 0 0,1 70,10 Z" fill="#10b981" />
        <circle cx="70" cy="70" r="28" fill="white" />
        <text x="70" y="74" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1f2937">{t('illustrations.budgetPieChart.center')}</text>
      </svg>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-info-500" />
          <span className="text-sm font-bold text-info-600">{t('illustrations.budgetPieChart.needs')}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded" style={{ background: '#f59e0b' }} />
          <span className="text-sm font-bold text-accent-700">{t('illustrations.budgetPieChart.wants')}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-success-500" />
          <span className="text-sm font-bold text-success-700">{t('illustrations.budgetPieChart.savings')}</span>
        </div>
      </div>
    </div>
  );
}
