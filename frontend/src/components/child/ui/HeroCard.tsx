import { motion } from 'framer-motion';
import { GradientButton } from './GradientButton';

type Props = { eyebrow: string; icon?: string; title: string; subtitle?: string; cta: string; to: string };

export function HeroCard({ eyebrow, icon, title, subtitle, cta, to }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}
      className="overflow-hidden rounded-3xl bg-gradient-to-br from-amber-400 to-orange-500 p-5 text-white shadow-lg shadow-orange-500/30"
    >
      <p className="text-xs font-extrabold uppercase tracking-wider opacity-95"><span aria-hidden="true">▶ </span>{eyebrow}</p>
      <div className="mt-2 flex items-center gap-3">
        {icon && <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-2xl" aria-hidden="true">{icon}</span>}
        <p className="text-lg font-extrabold leading-tight">{title}</p>
      </div>
      {subtitle && <p className="mt-1 text-sm font-medium opacity-90">{subtitle}</p>}
      <GradientButton to={to} full className="mt-4 !bg-none bg-white text-amber-700 shadow-none hover:bg-amber-50">{cta}<span aria-hidden="true"> →</span></GradientButton>
    </motion.div>
  );
}
