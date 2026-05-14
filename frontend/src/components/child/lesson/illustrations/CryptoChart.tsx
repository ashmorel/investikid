export function CryptoChart() {
  return (
    <div className="flex items-center justify-center rounded-xl bg-gradient-to-br from-amber-100 to-orange-100 p-6">
      <svg width="280" height="120" viewBox="0 0 280 120" aria-hidden="true">
        <line x1="30" y1="20" x2="30" y2="100" stroke="#fde68a" strokeWidth="1" />
        <line x1="30" y1="100" x2="270" y2="100" stroke="#fde68a" strokeWidth="1" />
        <line x1="30" y1="60" x2="270" y2="60" stroke="#fde68a" strokeWidth="0.5" strokeDasharray="4" />
        <polyline points="30,80 60,50 90,70 120,20 150,90 180,40 210,75 240,30 270,85" fill="none" stroke="#ea580c" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="248" cy="30" r="16" fill="#f59e0b" />
        <text x="248" y="36" textAnchor="middle" fontSize="18" fontWeight="800" fill="#fff">₿</text>
        <text x="150" y="115" textAnchor="middle" fontSize="10" fill="#92400e" fontWeight="600">↑ This is NOT "guaranteed money" ↑</text>
      </svg>
    </div>
  );
}
