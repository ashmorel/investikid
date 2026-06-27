import { GradientButton } from './GradientButton';

type Props = {
  eyebrow: string;
  icon?: string;
  title: string;
  subtitle?: string;
  cta: string;
  to: string;
  variant?: 'playful' | 'flat';
  onCtaClick?: () => void;
};

export function HeroCard({ eyebrow, icon, title, subtitle, cta, to, variant = 'playful', onCtaClick }: Props) {
  const flat = variant === 'flat';
  return (
    <div
      className={
        (flat
          ? 'overflow-hidden rounded-xl border border-gray-200 bg-white p-5 text-gray-900 shadow-sm'
          : 'overflow-hidden rounded-3xl bg-brand-gradient p-6 text-white shadow-lg shadow-brand-600/30') + ' animate-hero-card-in'
      }
    >
      <p className={`text-xs font-extrabold uppercase tracking-wider ${flat ? 'text-gray-500' : 'opacity-95'}`}>
        {!flat && <span aria-hidden="true">▶ </span>}{eyebrow}
      </p>
      <div className="mt-2 flex items-center gap-3">
        {icon && !flat && (
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-2xl" aria-hidden="true">{icon}</span>
        )}
        <p className="text-xl font-extrabold leading-tight">{title}</p>
      </div>
      {subtitle && <p className={`mt-1 text-sm font-medium ${flat ? 'text-gray-500' : 'opacity-90'}`}>{subtitle}</p>}
      <GradientButton
        to={to}
        full
        onClick={onCtaClick}
        className={
          flat
            ? 'mt-4 !bg-none bg-brand-700 text-white shadow-none hover:bg-brand-800'
            : 'mt-4 !bg-none bg-white text-brand-700 shadow-none hover:bg-brand-50'
        }
      >
        {cta}<span aria-hidden="true"> →</span>
      </GradientButton>
    </div>
  );
}
