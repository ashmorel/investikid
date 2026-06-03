import { useId } from 'react';

export function RobotEddie({ size = 48, className }: { size?: number; className?: string }) {
  const uid = useId();
  const gradId = `eddie-antenna-${uid}`;
  return (
    <svg width={size} height={size} viewBox="0 0 48 50" fill="none" aria-hidden="true" className={className}>
      <rect x="22.5" y="1" width="3" height="9" rx="1.5" fill="#8b93a3" />
      <circle cx="24" cy="3" r="4" fill={`url(#${gradId})`} />
      <rect x="2" y="9" width="44" height="40" rx="13" fill="#6b95eb" />
      <rect x="7" y="17" width="34" height="24" rx="9" fill="#1d2647" />
      <circle cx="17.5" cy="29" r="3.5" fill="#66e0ff" />
      <circle cx="30.5" cy="29" r="3.5" fill="#66e0ff" />
      <defs>
        <linearGradient id={gradId} x1="20" y1="-1" x2="28" y2="7" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fbbf24" />
          <stop offset="1" stopColor="#f97316" />
        </linearGradient>
      </defs>
    </svg>
  );
}
