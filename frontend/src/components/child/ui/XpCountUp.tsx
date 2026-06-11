import { useEffect, useState } from 'react';
import { animate, useReducedMotion } from 'framer-motion';

type Props = { value: number; className?: string };

/**
 * Animated XP number roll, 0 → value over ~0.8s (juice pack, spec D).
 * Reduced motion renders the final value instantly. Screen readers get the
 * final value once via visually-hidden text — the rolling digits are
 * aria-hidden so SRs aren't spammed with every tick.
 */
export function XpCountUp({ value, className }: Props) {
  const reducedMotion = useReducedMotion();
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (reducedMotion) return;
    const controls = animate(0, value, {
      duration: 0.8,
      ease: 'easeOut',
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    return () => controls.stop();
  }, [value, reducedMotion]);

  // Reduced motion renders the final value directly — no animation, no setState.
  const shown = reducedMotion ? value : display;

  return (
    <span className={className}>
      <span className="sr-only">{`+${value} XP`}</span>
      <span aria-hidden="true">+{shown}</span>
    </span>
  );
}
