import { useId } from 'react';
import { SKIN } from './pennyScenes';

type Mood = 'happy' | 'thinking' | 'excited';

const MOOD_GRADIENT: Record<Mood, [string, string]> = {
  happy: ['#38bdf8', '#2563eb'],     // sky-400 → blue-600
  thinking: ['#818cf8', '#4f46e5'],  // indigo-400 → indigo-600
  excited: ['#f59e0b', '#f43f5e'],   // amber-500 → rose-500
};

// Accessory overlays (M8 Penny's Shop) — hand-drawn flat SVG anchored on/over
// the head, matching the scene-background art style. Keyed by CosmeticItem.slug;
// unknown slugs render nothing (forward-compatible). Coordinates are in the
// 0–56 Penny viewBox. Eyes sit at (21,26) and (35,26); top of head ≈ y2.
const ACCESSORY_SVG: Record<string, JSX.Element> = {
  // Party hat: striped cone + base band + pom-pom.
  party_hat: (
    <>
      <polygon points="28,1 19,17 37,17" fill="#ec4899" />
      <polygon points="28,1 24.5,8 30,8" fill="#fde047" />
      <polygon points="22,12 33.5,12 35,17 20.5,17" fill="#fde047" />
      <ellipse cx="28" cy="17" rx="9.5" ry="2.2" fill="#be185d" />
      <circle cx="28" cy="2.5" r="2.4" fill="#facc15" />
    </>
  ),
  // Sunglasses: two lenses + bridge + shine.
  sunglasses: (
    <>
      <rect x="15" y="22" width="12" height="8" rx="3" fill="#1f2937" />
      <rect x="29" y="22" width="12" height="8" rx="3" fill="#1f2937" />
      <rect x="26" y="24.5" width="4" height="1.8" fill="#1f2937" />
      <rect x="17" y="23.5" width="3.5" height="1.6" rx="0.8" fill="#fff" fillOpacity="0.45" />
      <rect x="31" y="23.5" width="3.5" height="1.6" rx="0.8" fill="#fff" fillOpacity="0.45" />
    </>
  ),
  // Hair bow on the top-right of the head.
  bow: (
    <>
      <polygon points="40,12 33,8 33,16" fill="#ec4899" />
      <polygon points="40,12 47,8 47,16" fill="#ec4899" />
      <polygon points="40,12 34.5,9.5 34.5,14.5" fill="#f9a8d4" />
      <polygon points="40,12 45.5,9.5 45.5,14.5" fill="#f9a8d4" />
      <circle cx="40" cy="12" r="2.3" fill="#be185d" />
    </>
  ),
  // Headphones: band over the top + two ear cups.
  headphones: (
    <>
      <path d="M9 24 Q28 1 47 24" stroke="#1f2937" strokeWidth="2.6" fill="none" />
      <rect x="6" y="18" width="7.5" height="11" rx="3.5" fill="#1f2937" />
      <rect x="42.5" y="18" width="7.5" height="11" rx="3.5" fill="#1f2937" />
      <rect x="8" y="20.5" width="3.5" height="6" rx="1.75" fill="#6b7280" />
      <rect x="44.5" y="20.5" width="3.5" height="6" rx="1.75" fill="#6b7280" />
    </>
  ),
  // Graduation cap: mortarboard + tassel.
  grad_cap: (
    <>
      <path d="M22 11 Q28 15 34 11 L34 13 Q28 17 22 13 Z" fill="#1f2937" />
      <polygon points="28,4 41,9 28,14 15,9" fill="#111827" />
      <circle cx="28" cy="9" r="1.4" fill="#facc15" />
      <path d="M28 9 L39 9.5" stroke="#facc15" strokeWidth="0.8" fill="none" />
      <line x1="39" y1="9.5" x2="39" y2="15" stroke="#facc15" strokeWidth="0.8" />
      <circle cx="39" cy="15.5" r="1.3" fill="#fbbf24" />
    </>
  ),
  // Crown: gold band + points + jewels.
  crown: (
    <>
      <polygon points="18,12 18,5 23,9 28,3 33,9 38,5 38,12" fill="#fbbf24" />
      <rect x="18" y="11" width="20" height="3.5" rx="1" fill="#f59e0b" />
      <circle cx="22" cy="12.7" r="1" fill="#ef4444" />
      <circle cx="28" cy="12.7" r="1" fill="#3b82f6" />
      <circle cx="34" cy="12.7" r="1" fill="#22c55e" />
    </>
  ),
  // Monocle: gold ring over the right eye + chain.
  monocle: (
    <>
      <circle cx="35" cy="26" r="6.5" fill="#fff" fillOpacity="0.12" stroke="#d4af37" strokeWidth="1.3" />
      <path d="M40 30 Q43 36 40.5 41" stroke="#d4af37" strokeWidth="1" fill="none" />
    </>
  ),
  // Top hat: brim + cylinder crown + band.
  top_hat: (
    <>
      <ellipse cx="28" cy="15" rx="13" ry="2.6" fill="#1f2937" />
      <rect x="21" y="2" width="14" height="13" rx="1.5" fill="#1f2937" />
      <rect x="21" y="10.5" width="14" height="2.6" fill="#ef4444" />
    </>
  ),
  // ── Limited-drop accessories (B-programme pool art) ──────────────────────
  // Halo: golden ring floating above the head (own slot — always stacks).
  halo: (
    <>
      <ellipse cx="28" cy="4" rx="9" ry="2.8" fill="#fde68a" fillOpacity="0.35" />
      <ellipse cx="28" cy="4" rx="9" ry="2.8" fill="none" stroke="#fbbf24" strokeWidth="2" />
    </>
  ),
  // Winter beanie: red dome + white fold band + pom-pom (head slot).
  winter_beanie: (
    <>
      <path d="M13 18 Q28 2 43 18 Z" fill="#ef4444" />
      <rect x="12" y="16" width="32" height="5" rx="2.5" fill="#f8fafc" />
      <circle cx="28" cy="4" r="2.8" fill="#f8fafc" />
    </>
  ),
  // Flower crown: green vine + a row of little flowers (head slot).
  flower_crown: (
    <>
      <path d="M12 18 Q28 10 44 18" stroke="#22c55e" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      <circle cx="14" cy="16" r="2.6" fill="#f472b6" /><circle cx="14" cy="16" r="1" fill="#fde047" />
      <circle cx="22" cy="13" r="2.6" fill="#fb7185" /><circle cx="22" cy="13" r="1" fill="#fde047" />
      <circle cx="28" cy="12" r="2.8" fill="#c084fc" /><circle cx="28" cy="12" r="1.1" fill="#fde047" />
      <circle cx="34" cy="13" r="2.6" fill="#fb7185" /><circle cx="34" cy="13" r="1" fill="#fde047" />
      <circle cx="42" cy="16" r="2.6" fill="#f472b6" /><circle cx="42" cy="16" r="1" fill="#fde047" />
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
      {/* Ears — body-toned outer + soft pink inner */}
      <ellipse cx="11" cy="20" rx="6" ry="7" fill={from} />
      <ellipse cx="45" cy="20" rx="6" ry="7" fill={from} />
      <ellipse cx="11" cy="21" rx="3" ry="3.6" fill="#fbcfe8" />
      <ellipse cx="45" cy="21" rx="3" ry="3.6" fill="#fbcfe8" />
      {/* Head + soft top highlight */}
      <circle cx="28" cy="28" r="26" fill={`url(#${gradId})`} />
      <ellipse cx="28" cy="17" rx="16" ry="10" fill="white" fillOpacity="0.2" />
      {/* Rosy cheeks */}
      <circle cx="16" cy="33" r="3.3" fill="#fb7185" fillOpacity="0.5" />
      <circle cx="40" cy="33" r="3.3" fill="#fb7185" fillOpacity="0.5" />
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
          <ellipse cx="21" cy="26" rx="4" ry="3.6" fill="white" />
          <ellipse cx="35" cy="26" rx="4" ry="3.6" fill="white" />
          <circle cx={mood === 'thinking' ? 22 : 21.5} cy="26.5" r="2.1" fill="#0c4a6e" />
          <circle cx={mood === 'thinking' ? 36 : 35.5} cy="26.5" r="2.1" fill="#0c4a6e" />
          {/* glossy catch-light */}
          <circle cx={mood === 'thinking' ? 22.8 : 22.3} cy="25.4" r="0.85" fill="white" />
          <circle cx={mood === 'thinking' ? 36.8 : 36.3} cy="25.4" r="0.85" fill="white" />
        </>
      )}
      {/* Snout — pink with nostrils */}
      <ellipse cx="28" cy="35" rx="6.4" ry="4.4" fill="#f9a8d4" fillOpacity="0.95" />
      <ellipse cx="25.6" cy="35" rx="1" ry="1.3" fill="#9d174d" />
      <ellipse cx="30.4" cy="35" rx="1" ry="1.3" fill="#9d174d" />
      {/* Mouth */}
      <path
        d={mood === 'excited' ? 'M22 40 Q28 46 34 40' : 'M23 39 Q28 44 33 39'}
        stroke="#0c4a6e"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
      {accSlugs.map((slug) => {
        const art = ACCESSORY_SVG[slug];
        return art ? <g key={slug} data-accessory={slug}>{art}</g> : null;
      })}
    </svg>
  );
}
