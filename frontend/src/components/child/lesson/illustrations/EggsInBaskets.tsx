import { useTranslation } from 'react-i18next';

export function EggsInBaskets() {
  const { t } = useTranslation('child');
  return (
    <div className="flex items-end justify-center gap-8 rounded-xl bg-gradient-to-br from-blue-100 to-purple-100 p-6">
      <div className="text-center">
        <svg width="70" height="80" viewBox="0 0 70 80" aria-hidden="true">
          <ellipse cx="35" cy="65" rx="30" ry="12" fill="#d97706" />
          <rect x="5" y="40" width="60" height="25" rx="4" fill="#f59e0b" />
          <line x1="5" y1="45" x2="65" y2="45" stroke="#d97706" strokeWidth="1.5" />
          <line x1="5" y1="52" x2="65" y2="52" stroke="#d97706" strokeWidth="1.5" />
          <ellipse cx="22" cy="36" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <ellipse cx="38" cy="34" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <ellipse cx="50" cy="36" rx="9" ry="11" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          <line x1="20" y1="10" x2="50" y2="30" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
          <line x1="50" y1="10" x2="20" y2="30" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <p className="text-xs font-bold text-danger-600 mt-1">{t('illustrations.eggs.allInOne')}</p>
      </div>
      <div className="text-center">
        <div className="flex gap-1.5">
          <svg width="50" height="65" viewBox="0 0 50 65" aria-hidden="true">
            <ellipse cx="25" cy="52" rx="22" ry="10" fill="#d97706" />
            <rect x="3" y="32" width="44" height="20" rx="3" fill="#f59e0b" />
            <line x1="3" y1="37" x2="47" y2="37" stroke="#d97706" strokeWidth="1" />
            <line x1="3" y1="43" x2="47" y2="43" stroke="#d97706" strokeWidth="1" />
            <ellipse cx="17" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
            <ellipse cx="33" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          </svg>
          <svg width="50" height="65" viewBox="0 0 50 65" aria-hidden="true">
            <ellipse cx="25" cy="52" rx="22" ry="10" fill="#d97706" />
            <rect x="3" y="32" width="44" height="20" rx="3" fill="#f59e0b" />
            <line x1="3" y1="37" x2="47" y2="37" stroke="#d97706" strokeWidth="1" />
            <line x1="3" y1="43" x2="47" y2="43" stroke="#d97706" strokeWidth="1" />
            <ellipse cx="25" cy="28" rx="7" ry="9" fill="#fef3c7" stroke="#fbbf24" strokeWidth="1.5" />
          </svg>
        </div>
        <p className="text-xs font-bold text-success-600 mt-1">{t('illustrations.eggs.spreadOut')}</p>
      </div>
    </div>
  );
}
