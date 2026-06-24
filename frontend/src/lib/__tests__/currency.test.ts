import { describe, it, expect } from 'vitest';
import { formatCurrency, getCurrencySymbol } from '../currency';

describe('getCurrencySymbol', () => {
  it('maps known codes and falls back to the code itself', () => {
    expect(getCurrencySymbol('USD')).toBe('$');
    expect(getCurrencySymbol('GBP')).toBe('£');
    expect(getCurrencySymbol('XYZ')).toBe('XYZ');
  });
});

describe('formatCurrency', () => {
  it('formats numbers and numeric strings to two decimals', () => {
    expect(formatCurrency(1240.5, 'USD')).toBe('$1,240.50 USD');
    expect(formatCurrency('1240.5', 'GBP')).toBe('£1,240.50 GBP');
  });

  it('degrades to zero (never throws) for null/undefined/NaN', () => {
    // Regression: undefined value used to crash the whole page via
    // num.toLocaleString — e.g. the Simulator portfolio hero during loading.
    expect(() => formatCurrency(undefined, 'USD')).not.toThrow();
    expect(formatCurrency(undefined, 'USD')).toBe('$0.00 USD');
    expect(formatCurrency(null, 'USD')).toBe('$0.00 USD');
    expect(formatCurrency('not-a-number', 'USD')).toBe('$0.00 USD');
  });
});
