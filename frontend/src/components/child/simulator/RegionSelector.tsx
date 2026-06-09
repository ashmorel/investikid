import type { KeyboardEvent } from 'react';
import { REGIONS, type RegionCode } from '@/lib/region';

type Props = { value: RegionCode; onChange: (region: RegionCode) => void };

export function RegionSelector({ value, onChange }: Props) {
  const codes = REGIONS.map((r) => r.code);

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const idx = codes.indexOf(value);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      onChange(codes[(idx + 1) % codes.length]);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      onChange(codes[(idx - 1 + codes.length) % codes.length]);
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label="Market region"
      onKeyDown={onKeyDown}
      className="inline-flex rounded-full border border-brand-200 bg-brand-50 p-0.5"
    >
      {REGIONS.map((r) => {
        const selected = r.code === value;
        return (
          <button
            key={r.code}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(r.code)}
            className={`inline-flex min-h-[40px] items-center gap-1.5 rounded-full px-3 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500 ${
              selected ? 'bg-brand-600 text-white' : 'text-brand-700 hover:bg-brand-100'
            }`}
          >
            <span aria-hidden="true">{r.flag}</span>
            <span>{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
