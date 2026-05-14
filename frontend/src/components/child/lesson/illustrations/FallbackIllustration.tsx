const TOPIC_EMOJI: Record<string, string> = {
  stocks: '📈',
  savings: '🏦',
  real_estate: '🏠',
  budgeting: '💰',
  risk: '🎲',
  crypto: '₿',
  taxes: '🧾',
  debt: '💳',
  entrepreneurship: '🚀',
};

export function FallbackIllustration({ topic }: { topic: string }) {
  const emoji = TOPIC_EMOJI[topic] ?? '📚';
  return (
    <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 py-8">
      <span className="text-6xl">{emoji}</span>
    </div>
  );
}
