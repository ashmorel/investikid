import { Penny } from './Penny';
import { BACKGROUND } from './pennyScenes';

export function AvatarStage({
  background, skin, accessories, label,
}: { background?: string | null; skin?: string | null; accessories?: string[]; label: string }) {
  const scene = background ? BACKGROUND[background] : null;
  return (
    <div
      role="img"
      aria-label={label}
      className="relative mx-auto flex h-44 w-44 items-center justify-center overflow-hidden rounded-3xl border border-brand-200 bg-brand-50"
    >
      {scene && (
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
        >
          {scene}
        </svg>
      )}
      <Penny size={120} skin={skin} accessories={accessories} className="relative" />
    </div>
  );
}
