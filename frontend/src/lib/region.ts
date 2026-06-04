export type RegionCode = 'US' | 'GB' | 'HK';

export const REGIONS: { code: RegionCode; flag: string; label: string }[] = [
  { code: 'US', flag: '🇺🇸', label: 'US' },
  { code: 'GB', flag: '🇬🇧', label: 'UK' },
  { code: 'HK', flag: '🇭🇰', label: 'HK' },
];

// Exchanges featured first in the simulator for each region.
export const REGION_EXCHANGES: Record<RegionCode, string[]> = {
  US: ['NASDAQ', 'NYSE'],
  GB: ['LSE'],
  HK: ['HKEX'],
};

export const MAJOR_CURRENCIES = ['USD', 'GBP', 'HKD'] as const;

/** Practice-currency options: the child's current currency plus the majors, deduped. */
export function currencyOptions(currentCurrency: string): string[] {
  return Array.from(new Set([currentCurrency, ...MAJOR_CURRENCIES]));
}
