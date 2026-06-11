export function StatChip({ emoji, value, label }: { emoji: string; value: React.ReactNode; label: string }) {
  return (
    <div className="flex flex-1 flex-col items-center rounded-2xl border border-brand-200 bg-white px-2 py-2.5 shadow-sm">
      <span className="text-lg" aria-hidden="true">{emoji}</span>
      <span className="text-base font-extrabold text-gray-900">{value}</span>
      <span className="text-[11px] font-medium text-gray-500">{label}</span>
    </div>
  );
}
