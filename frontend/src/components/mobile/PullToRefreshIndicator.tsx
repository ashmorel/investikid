type Props = {
  visible: boolean;
  progress: number;
};

export function PullToRefreshIndicator({ visible, progress }: Props) {
  if (!visible) return null;
  const isRefreshing = progress >= 1;

  return (
    <div
      className="flex justify-center py-2"
      role="status"
      aria-label={isRefreshing ? 'Refreshing' : 'Pull to refresh'}
    >
      <div
        className={`h-6 w-6 rounded-full border-2 border-brand-500 border-t-transparent ${
          isRefreshing ? 'animate-spin' : ''
        }`}
        style={{
          opacity: Math.max(progress, 0.3),
          transform: `rotate(${progress * 360}deg)`,
        }}
      />
    </div>
  );
}
