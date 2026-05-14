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

export function formatCurrency(value: string | number, currencyCode: string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${getCurrencySymbol(currencyCode)}${formatted} ${currencyCode}`;
}
