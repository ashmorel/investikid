type ReviewBannerProps = {
  dueCount: number;
};

export function ReviewBanner({ dueCount }: ReviewBannerProps) {
  if (dueCount <= 0) return null;

  const conceptText = dueCount === 1 ? '1 concept to practise' : `${dueCount} concepts to practise`;

  return (
    <div
      role="alert"
      className="rounded-2xl bg-gradient-to-r from-purple-600 to-purple-400 p-4 flex items-center gap-3"
    >
      <span className="text-2xl" aria-hidden="true">🔔</span>
      <div>
        <p className="text-white font-semibold text-sm">Time to review!</p>
        <p className="text-purple-100 text-xs">
          You have {conceptText} — keep your streak going!
        </p>
      </div>
    </div>
  );
}
