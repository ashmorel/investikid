import { useId } from 'react';

type Mood = 'happy' | 'thinking' | 'excited';

const MOOD_GRADIENT: Record<Mood, [string, string]> = {
  happy: ['#38bdf8', '#2563eb'],     // sky-400 → blue-600
  thinking: ['#818cf8', '#4f46e5'],  // indigo-400 → indigo-600
  excited: ['#f59e0b', '#f43f5e'],   // amber-500 → rose-500
};

export function Penny({
  size = 48,
  mood = 'happy',
  className,
}: {
  size?: number;
  mood?: Mood;
  className?: string;
}) {
  const uid = useId();
  const gradId = `penny-${uid}`;
  const [from, to] = MOOD_GRADIENT[mood];
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
          <text x="16" y="31" fontSize="11" fill="white">★</text>
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
    </svg>
  );
}
