interface OrderArrowsProps {
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export default function OrderArrows({ onMoveUp, onMoveDown, isFirst, isLast }: OrderArrowsProps) {
  return (
    <div className="flex gap-1">
      <button
        type="button"
        onClick={onMoveUp}
        disabled={isFirst}
        aria-label="Move up"
        className="rounded px-1 text-muted-foreground hover:text-ink disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ↑
      </button>
      <button
        type="button"
        onClick={onMoveDown}
        disabled={isLast}
        aria-label="Move down"
        className="rounded px-1 text-muted-foreground hover:text-ink disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ↓
      </button>
    </div>
  );
}
