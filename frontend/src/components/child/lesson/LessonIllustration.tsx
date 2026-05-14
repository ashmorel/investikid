import type { ComponentType } from 'react';
import { BudgetPieChart } from './illustrations/BudgetPieChart';
import { EggsInBaskets } from './illustrations/EggsInBaskets';
import { CryptoChart } from './illustrations/CryptoChart';
import { FallbackIllustration } from './illustrations/FallbackIllustration';

const ILLUSTRATION_MAP: Record<string, ComponentType> = {
  'The 50/30/20 rule': BudgetPieChart,
  'Which portfolio is more diversified?': EggsInBaskets,
  "Your friend's hot stock tip": EggsInBaskets,
  'Build a simple portfolio': EggsInBaskets,
  'True or false about crypto': CryptoChart,
  'Classmate says crypto is guaranteed money': CryptoChart,
  'Crypto vs stocks vs savings': CryptoChart,
};

type Props = {
  lessonTitle: string;
  topic: string;
};

export function LessonIllustration({ lessonTitle, topic }: Props) {
  const Illustration = ILLUSTRATION_MAP[lessonTitle];
  if (Illustration) return <Illustration />;
  return <FallbackIllustration topic={topic} />;
}
