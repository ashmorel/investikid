import { Penny } from './Penny';
import { BACKGROUND } from './pennyScenes';

export function AvatarStage({
  background, skin, accessories, label, hero = false,
}: { background?: string | null; skin?: string | null; accessories?: string[]; label: string; hero?: boolean }) {
  const scene = background ? BACKGROUND[background] : null;
  return (
    <div
      role="img"
      aria-label={label}
      className={`relative mx-auto flex items-center justify-center overflow-hidden border-brand-200 bg-brand-50 ${
        hero ? 'h-60 w-full rounded-[1.75rem] border shadow-sm' : 'h-44 w-44 rounded-3xl border'
      }`}
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
      <Penny size={hero ? 168 : 120} skin={skin} accessories={accessories} className="relative" />
    </div>
  );
}
