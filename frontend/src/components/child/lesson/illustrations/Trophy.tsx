export function Trophy() {
  return (
    <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true" className="mx-auto">
      <circle cx="20" cy="25" r="3" fill="#fbbf24" opacity="0.7" />
      <circle cx="100" cy="20" r="2" fill="#f59e0b" opacity="0.6" />
      <circle cx="15" cy="60" r="2" fill="#fde68a" opacity="0.8" />
      <circle cx="105" cy="55" r="3" fill="#fde68a" opacity="0.7" />
      <text x="10" y="45" fontSize="14" fill="#fbbf24">✦</text>
      <text x="100" y="40" fontSize="10" fill="#f59e0b">✦</text>
      <text x="25" y="85" fontSize="8" fill="#fde68a">✦</text>
      <text x="95" y="80" fontSize="12" fill="#fbbf24">✦</text>
      <rect x="45" y="85" width="30" height="8" rx="2" fill="#d97706" />
      <rect x="50" y="75" width="20" height="12" rx="1" fill="#f59e0b" />
      <path d="M35,30 Q35,70 50,75 L70,75 Q85,70 85,30 Z" fill="#fbbf24" />
      <path d="M40,35 Q40,65 52,70 L68,70 Q80,65 80,35 Z" fill="#f59e0b" />
      <text x="60" y="58" textAnchor="middle" fontSize="24" fill="#fff">⭐</text>
      <path d="M35,35 Q20,35 20,50 Q20,65 35,65" fill="none" stroke="#fbbf24" strokeWidth="4" strokeLinecap="round" />
      <path d="M85,35 Q100,35 100,50 Q100,65 85,65" fill="none" stroke="#fbbf24" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}
