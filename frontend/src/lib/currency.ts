const SYMBOLS: Record<string, string> = {
  USD: '$',
  GBP: '£',
  HKD: 'HK$',
  EUR: '€',
  JPY: '¥',
};

export function getCurrencySymbol(code: string): string {
  return SYMBOLS[code] ?? code;
}

export function formatCurrency(value: string | number | null | undefined, currencyCode: string): string {
  // Tolerate null/undefined/NaN (transient loading or partial API data) by
  // showing a zero amount rather than throwing — a crash here takes down the
  // whole page (e.g. the Simulator portfolio hero).
  const raw = typeof value === 'string' ? parseFloat(value) : value;
  const num = typeof raw === 'number' && Number.isFinite(raw) ? raw : 0;
  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${getCurrencySymbol(currencyCode)}${formatted} ${currencyCode}`;
}
