export function BudgetPieChart() {
  return (
    <div className="flex items-center justify-center gap-6 rounded-xl bg-gradient-to-br from-amber-100 to-amber-200 p-6">
      <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
        <circle cx="70" cy="70" r="60" fill="#dbeafe" />
        <path d="M70,70 L70,10 A60,60 0 0,1 122,100 Z" fill="#3b82f6" />
        <path d="M70,70 L122,100 A60,60 0 0,1 18,100 Z" fill="#f59e0b" />
        <path d="M70,70 L18,100 A60,60 0 0,1 70,10 Z" fill="#10b981" />
        <circle cx="70" cy="70" r="28" fill="white" />
        <text x="70" y="74" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1f2937">Budget</text>
      </svg>
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-blue-500" />
          <span className="text-sm font-bold text-blue-800">50% Needs</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-amber-500" />
          <span className="text-sm font-bold text-amber-800">30% Wants</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3.5 w-3.5 rounded bg-green-500" />
          <span className="text-sm font-bold text-green-800">20% Savings</span>
        </div>
      </div>
    </div>
  );
}
