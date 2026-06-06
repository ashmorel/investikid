import { Penny } from '@/components/child/ui/Penny';
import { useAgeTier } from '@/lib/ageTier';
import { ENCOURAGEMENT } from '@/lib/tierCopy';

interface LessonChromeProps {
  /** 1-based current lesson position within the level */
  position: number;
  /** Total lessons in the level (0 = unknown) */
  total: number;
  /** XP reward shown as a badge */
  xpReward: number;
  /** Called when the back chevron is pressed */
  onBack: () => void;
}

/**
 * Lesson progress header: back control + progress bar + XP badge + Penny speech bubble.
 * Rendered above the active lesson renderer; never shown on the CompletionPanel screen.
 */
export function LessonChrome({ position, total, xpReward, onBack }: LessonChromeProps) {
  // Pick a stable line based on position so it doesn't change on re-render
  const lines = ENCOURAGEMENT[useAgeTier()];
  const line = lines[(position - 1) % lines.length];
  const pct = total > 0 ? Math.min(100, Math.round(((position - 1) / total) * 100)) : 0;

  return (
    <div className="mb-4 space-y-2">
      {/* Row 1: back + progress bar + XP */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label="Go back"
          onClick={onBack}
          className="flex-shrink-0 rounded-full p-1 text-brand-700 hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" clipRule="evenodd"
              d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" />
          </svg>
        </button>

        {/* Progress track */}
        <div
          role="progressbar"
          aria-valuenow={Math.max(0, position - 1)}
          aria-valuemin={0}
          aria-valuemax={total || 1}
          aria-label={total > 0 ? `Lesson ${position} of ${total}` : `Lesson ${position}`}
          className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-brand-100"
        >
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-brand-gradient transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Count label */}
        {total > 0 && (
          <span className="flex-shrink-0 text-xs font-semibold text-brand-700 tabular-nums">
            {position}/{total}
          </span>
        )}

        {/* XP badge */}
        <span className="flex-shrink-0 rounded-lg bg-accent-100 px-2.5 py-1 text-xs font-semibold text-accent-700">
          🏆 {xpReward} XP
        </span>
      </div>

      {/* Row 2: Penny + speech bubble */}
      <div className="flex items-center gap-2">
        <Penny size={40} mood="thinking" />
        {/* Penny speech bubble */}
        <div className="relative rounded-2xl rounded-tl-none bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-brand-200">
          {line}
          {/* Tail */}
          <span
            aria-hidden="true"
            className="absolute -left-2 top-2 border-4 border-transparent border-r-white"
          />
        </div>
      </div>
    </div>
  );
}
