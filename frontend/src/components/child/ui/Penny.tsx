import { useId } from 'react';
import { SKIN } from './pennyScenes';

type Mood = 'happy' | 'thinking' | 'excited';

const MOOD_GRADIENT: Record<Mood, [string, string]> = {
  happy: ['#38bdf8', '#2563eb'],     // sky-400 → blue-600
  thinking: ['#818cf8', '#4f46e5'],  // indigo-400 → indigo-600
  excited: ['#f59e0b', '#f43f5e'],   // amber-500 → rose-500
};

// Accessory overlays (M8 Penny's Shop) — emoji anchored above/on the head.
// Keyed by CosmeticItem.slug; unknown slugs render nothing (forward-compatible).
const ACCESSORY: Record<string, { glyph: string; x: number; y: number; size: number }> = {
  sunglasses: { glyph: '🕶️', x: 28, y: 30, size: 16 },
  bow: { glyph: '🎀', x: 40, y: 14, size: 14 },
  headphones: { glyph: '🎧', x: 28, y: 14, size: 16 },
  grad_cap: { glyph: '🎓', x: 28, y: 10, size: 18 },
  crown: { glyph: '👑', x: 28, y: 9, size: 18 },
  monocle: { glyph: '🧐', x: 36, y: 30, size: 14 },
  top_hat: { glyph: '🎩', x: 28, y: 8, size: 18 },
};

// Some accessories are hand-drawn flat-SVG (matching the scene backgrounds)
// rather than emoji — for items with no good emoji. Checked before ACCESSORY.
// Coordinates are in the 0–56 Penny viewBox, anchored on top of the head.
const ACCESSORY_SVG: Record<string, JSX.Element> = {
  // A proper party hat: striped cone + base band + pom-pom (no emoji face).
  party_hat: (
    <>
      <polygon points="28,1 19,17 37,17" fill="#ec4899" />
      {/* diagonal stripes */}
      <polygon points="28,1 24.5,8 30,8" fill="#fde047" />
      <polygon points="22,12 33.5,12 35,17 20.5,17" fill="#fde047" />
      <ellipse cx="28" cy="17" rx="9.5" ry="2.2" fill="#be185d" />
      <circle cx="28" cy="2.5" r="2.4" fill="#facc15" />
    </>
  ),
};

export function Penny({
  size = 48,
  mood = 'happy',
  accessory,
  accessories,
  skin,
  className,
}: {
  size?: number;
  mood?: Mood;
  accessory?: string | null;
  /** Multiple stacked accessory slugs (takes precedence over `accessory`). */
  accessories?: string[];
  skin?: string | null;
  className?: string;
}) {
  const uid = useId();
  const gradId = `penny-${uid}`;
  const skinPair = skin ? SKIN[skin] : undefined;
  const [from, to] = skinPair ?? MOOD_GRADIENT[mood];
  const accSlugs = accessories ?? (accessory ? [accessory] : []);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor={from} />
          <stop offset="1" stopColor={to} />
        </linearGradient>
      </defs>
      {/* Head */}
      <circle cx="28" cy="28" r="26" fill={`url(#${gradId})`} />
      <circle cx="28" cy="28" r="22" fill="white" fillOpacity="0.18" />
      {/* Ears */}
      <ellipse cx="10" cy="22" rx="5" ry="7" fill="white" fillOpacity="0.4" />
      <ellipse cx="46" cy="22" rx="5" ry="7" fill="white" fillOpacity="0.4" />
      {/* Eyes */}
      {mood === 'excited' ? (
        <>
          {/* eslint-disable-next-line i18next/no-literal-string */}
          <text x="16" y="31" fontSize="11" fill="white">★</text>
          {/* eslint-disable-next-line i18next/no-literal-string */}
          <text x="33" y="31" fontSize="11" fill="white">★</text>
        </>
      ) : (
        <>
          <ellipse cx="21" cy="26" rx="3.5" ry="3" fill="white" />
          <ellipse cx="35" cy="26" rx="3.5" ry="3" fill="white" />
          <circle cx={mood === 'thinking' ? 22 : 21.5} cy="26" r="2" fill="#0c4a6e" />
          <circle cx={mood === 'thinking' ? 36 : 35.5} cy="26" r="2" fill="#0c4a6e" />
        </>
      )}
      {/* Snout */}
      <ellipse cx="28" cy="35" rx="6" ry="4" fill="white" fillOpacity="0.35" />
      <circle cx="26" cy="35" r="1" fill="white" fillOpacity="0.7" />
      <circle cx="30" cy="35" r="1" fill="white" fillOpacity="0.7" />
      {/* Mouth */}
      <path
        d={mood === 'excited' ? 'M22 39 Q28 44 34 39' : 'M23 38 Q28 42 33 38'}
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
      {accSlugs.map((slug) => {
        const custom = ACCESSORY_SVG[slug];
        if (custom) return <g key={slug}>{custom}</g>;
        const a = ACCESSORY[slug];
        return a ? (
          <text
            key={slug}
            x={a.x}
            y={a.y}
            fontSize={a.size}
            textAnchor="middle"
            dominantBaseline="middle"
            // Without an explicit fill these emoji inherit fill="none" from the
            // <svg fill="none"> root and never paint. Colour emoji ignore the
            // fill colour for their coloured layers, so any non-none value works.
            fill="#1f2937"
          >
            {a.glyph}
          </text>
        ) : null;
      })}
    </svg>
  );
}
